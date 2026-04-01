import yaml
import os
import logging
import json
from datetime import datetime, timedelta

class PostingRulesService:
    def __init__(self, config_path: str, state_path: str = None):
        self.config_path = config_path
        self.state_path = state_path
        self.config = {}
        self.state = {}
        self.last_loaded = 0
        self.logger = logging.getLogger("PostingRulesService")
        self._load_config()
        self._load_state()

    def _load_config(self):
        try:
            if not os.path.exists(self.config_path):
                self.logger.error(f"Config file not found: {self.config_path}")
                return
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            self.last_loaded = os.path.getmtime(self.config_path)
            self.logger.info(f"Loaded posting rules from {self.config_path}")
        except Exception as e:
            self.logger.error(f"Error loading posting rules: {e}")

    def _load_state(self):
        if not self.state_path:
            return
        try:
            if os.path.exists(self.state_path):
                with open(self.state_path, 'r') as f:
                    self.state = json.load(f)
            else:
                self.state = {"platforms": {}}
        except Exception as e:
            self.logger.error(f"Error loading state: {e}")
            self.state = {"platforms": {}}

    def _save_state(self):
        if not self.state_path:
            return
        try:
            os.makedirs(os.path.dirname(self.state_path), exist_ok=True)
            with open(self.state_path, 'w') as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving state: {e}")

    def _check_reload(self):
        if os.path.exists(self.config_path):
            mtime = os.path.getmtime(self.config_path)
            if mtime > self.last_loaded:
                self._load_config()

    def can_post(self, platform: str, content_type: str = "general", current_time: datetime = None) -> bool:
        self._check_reload()
        if not current_time:
            current_time = datetime.utcnow()

        # 1. Check Guardrails (Mandatory)
        if not self._check_guardrails(platform, content_type):
            return False

        # 2. Check Timing Rules
        if not self._check_timing_rules(platform, current_time):
            return False

        # 3. Check Frequency Rules
        if not self._check_frequency_rules(platform, current_time):
            return False

        return True

    def record_post(self, platform: str, current_time: datetime = None):
        """
        Updates the state after a successful post.
        """
        if not current_time:
            current_time = datetime.utcnow()
        
        if platform not in self.state["platforms"]:
            self.state["platforms"][platform] = {"last_post": None, "daily_count": 0, "last_date": None}
            
        current_date = current_time.strftime("%Y-%m-%d")
        platform_state = self.state["platforms"][platform]
        
        if platform_state.get("last_date") != current_date:
            platform_state["daily_count"] = 1
            platform_state["last_date"] = current_date
        else:
            platform_state["daily_count"] += 1
            
        platform_state["last_post"] = current_time.isoformat()
        self._save_state()

    def _check_guardrails(self, platform: str, content_type: str) -> bool:
        if self.is_blocked_action(content_type):
            self.logger.warning(f"Action '{content_type}' blocked by mandatory guardrails.")
            return False

        if self.requires_manual_approval(platform, content_type):
            self.logger.info(f"Action '{content_type}' requires manual approval.")
            return False

        return True

    def is_blocked_action(self, content_type: str) -> bool:
        guardrails = self.config.get("guardrails", {})
        blocked_actions = guardrails.get("blocked_actions", [])
        return content_type in blocked_actions

    def requires_manual_approval(self, platform: str, content_type: str) -> bool:
        guardrails = self.config.get("guardrails", {})
        requires_approval = guardrails.get("requires_approval", [])
        if content_type in requires_approval:
            return True

        platform_config = self.config.get("platforms", {}).get(platform, {})
        platform_specific = platform_config.get("requires_approval", [])
        return content_type in platform_specific

    def _check_timing_rules(self, platform: str, current_time: datetime) -> bool:
        platform_config = self.config.get("platforms", {}).get(platform, {})
        windows = platform_config.get("posting_windows", [])
        
        if not windows:
            return True
            
        current_time_str = current_time.strftime("%H:%M")
        for window in windows:
            if window.get("start") <= current_time_str <= window.get("end"):
                return True
                
        self.logger.info(f"Post to {platform} rejected: outside windows ({current_time_str}).")
        return False

    def _check_frequency_rules(self, platform: str, current_time: datetime) -> bool:
        platform_config = self.config.get("platforms", {}).get(platform, {})
        max_per_day = platform_config.get("max_posts_per_day", 999)
        min_interval = platform_config.get("min_interval_minutes", 0)
        
        platform_state = self.state.get("platforms", {}).get(platform, {})
        if not platform_state:
            return True

        current_date = current_time.strftime("%Y-%m-%d")
        
        # Check daily limit
        if platform_state.get("last_date") == current_date:
            if platform_state.get("daily_count", 0) >= max_per_day:
                self.logger.info(f"Post to {platform} rejected: daily limit reached ({max_per_day}).")
                return False
        
        # Check interval
        last_post_str = platform_state.get("last_post")
        if last_post_str:
            last_post = datetime.fromisoformat(last_post_str)
            if (current_time - last_post).total_seconds() < min_interval * 60:
                self.logger.info(f"Post to {platform} rejected: interval too short.")
                return False
                
        return True

    def get_required_hashtags(self, platform: str) -> list:
        self._check_reload()
        return self.config.get("platforms", {}).get(platform, {}).get("required_hashtags", [])

    def validate_post(self, platform: str, post_data: dict) -> dict:
        self._check_reload()
        result = {
            "valid": True, 
            "errors": [], 
            "modified_content": post_data.get("content", ""),
            "platform_config": self.config.get("platforms", {}).get(platform, {})
        }
        
        if platform not in self.config.get("platforms", {}):
            result["valid"] = False
            result["errors"].append(f"Platform '{platform}' not configured.")
            return result

        if not self._check_guardrails(platform, post_data.get("content_type", "general")):
            result["valid"] = False
            result["errors"].append("Blocked by guardrails.")
            
        hashtags = self.get_required_hashtags(platform)
        if hashtags:
            for tag in hashtags:
                if tag.lower() not in result["modified_content"].lower():
                    result["modified_content"] += f" {tag}"
                    
        return result
