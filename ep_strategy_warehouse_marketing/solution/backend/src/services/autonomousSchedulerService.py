"""
Autonomous Scheduler Service for Strategy Warehouse Marketing Engine
Coordinates content generation, queue processing, and metrics collection.
Version: V20260321_1515 - D1
"""
import logging
import os
import signal
import sys
import time
import yaml
from datetime import datetime, UTC, timedelta
from typing import Optional

# Services and Connectors
from src.models.database import SessionLocal
from src.services.contentGeneratorService import ContentGeneratorService, StrategyWarehouseDataLoader
from src.services.contentQueueService import ContentQueueService
from src.services.healthMonitorService import HealthMonitorService
from src.services.killSwitchService import KillSwitchService
from src.services.postingRulesService import PostingRulesService

# Models
from src.models.ContentQueue import QueueStatus

class AutonomousSchedulerService:
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = {}
        self.running = False
        self.logger = logging.getLogger("AutonomousScheduler")
        self._setup_logging()
        self._load_config()
        
        # Initialize Services (some might be lazy-loaded)
        self.db = SessionLocal()
        self.posting_rules = PostingRulesService(
            config_path="src/config/posting_rules.yaml",
            state_path="data/posting_state.json"
        )
        self.queue_service = ContentQueueService(self.db, self.posting_rules)
        self.kill_switch_service = KillSwitchService(self.db)
        self.generator_service = ContentGeneratorService()
        # Connectors (Mocked for now if credentials missing, but would be initialized here)
        self.connectors = {}
        self._init_connectors()
        self.health_monitor = HealthMonitorService(
            config_path="src/config/alerting_config.yaml",
            queue_service=self.queue_service,
            connectors=self.connectors,
            logger=self.logger,
        )
        self.data_loader = StrategyWarehouseDataLoader(
            base_path=self.config.get("jobs", {}).get("content_generation", {}).get("data_source_path", "data/warehouse")
        )
        # Job Tracking
        self.last_run = {
            "content_generation": datetime.min,
            "queue_processing": datetime.min,
            "metrics_collection": datetime.min,
            "health_monitoring": datetime.min,
            "heartbeat": datetime.min
        }

    def _setup_logging(self):
        os.makedirs("logs", exist_ok=True)
        handler = logging.FileHandler("logs/scheduler.log")
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        if not self.logger.handlers:
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        # Also log to stdout for visibility
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def _load_config(self):
        try:
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            self.logger.info(f"Loaded scheduler configuration from {self.config_path}")
        except Exception as e:
            self.logger.error(f"Error loading scheduler config: {e}")
            # Use defaults if config fails
            self.config = {
                "scheduler": {"heartbeat_interval_seconds": 60, "main_loop_interval_seconds": 30},
                "jobs": {
                    "content_generation": {"interval_minutes": 60, "enabled": True},
                    "queue_processing": {"interval_seconds": 60, "enabled": True},
                    "metrics_collection": {"interval_hours": 6, "enabled": True},
                    "health_monitoring": {"interval_minutes": 15, "enabled": True}
                }
            }

    def _init_connectors(self):
        # In a real scenario, we'd load credentials from env and initialize B1-B6
        # For D1, we log initialization
        self.logger.info("Initializing platform connectors...")
        # Example for Twitter (B1)
        # from src.connectors.twitterConnector import TwitterConnector
        # from src.models.TwitterAuth import TwitterConfig, TwitterAuth
        # if os.getenv("TWITTER_API_KEY"):
        #     tw_config = TwitterConfig(auth=TwitterAuth(...))
        #     self.connectors["twitter"] = TwitterConnector(tw_config)
        pass

    def start(self):
        self.logger.info("Starting Autonomous Scheduler Service...")
        self.running = True
        
        # Graceful shutdown handlers
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        try:
            while self.running:
                self._run_scheduler_loop()
                time.sleep(self.config["scheduler"].get("main_loop_interval_seconds", 30))
        except Exception as e:
            self.logger.critical(f"Critical error in scheduler loop: {e}")
            self.stop()

    def stop(self, *args):
        self.logger.info("Gracefully shutting down scheduler...")
        self.running = False
        if self.db:
            self.db.close()
        self.logger.info("Scheduler shutdown complete.")

    def _run_scheduler_loop(self):
        now = datetime.now()
        
        # 1. Heartbeat (registers status)
        self._check_heartbeat(now)
        
        # 2. Content Generation Job
        self._check_content_generation(now)
        
        # 3. Queue Processing Job
        self._check_queue_processing(now)
        
        # 4. Metrics Collection Job
        self._check_metrics_collection(now)
        
        # 5. Health Monitoring Job
        self._check_health_monitoring(now)

    def _check_heartbeat(self, now: datetime):
        interval = self.config["scheduler"].get("heartbeat_interval_seconds", 60)
        if (now - self.last_run["heartbeat"]).total_seconds() >= interval:
            self.logger.info("Scheduler Heartbeat - Running at %s", now.isoformat())
            # Here we could update a database table ServiceStatus
            self.last_run["heartbeat"] = now
            self.health_monitor.record_scheduler_heartbeat(now)

    def _check_content_generation(self, now: datetime):
        job_config = self.config["jobs"].get("content_generation", {})
        if not job_config.get("enabled", False):
            return
            
        interval = job_config.get("interval_minutes", 60)
        if (now - self.last_run["content_generation"]) >= timedelta(minutes=interval):
            self.logger.info("Job: Running Content Generation...")
            try:
                # Load latest warehouse data
                bundle = self.data_loader.load_snapshot_bundle()
                self.logger.info(f"Loaded snapshot data from {bundle['snapshot_dir']}")
                
                # Generate campaign bundle
                campaign = self.generator_service.generate_campaign_bundle(bundle)
                
                # Add generated posts to queue
                from src.schemas.content_schema import PublishableContent
                from pydantic import parse_obj_as
                
                for post_dict in campaign["posts"]:
                    # Create PublishableContent object from dict (assuming generator output matches schema)
                    # For MVP we might need to handle ID generation if missing
                    post = PublishableContent(**post_dict)
                    items = self.queue_service.add_to_queue(post)
                    self.logger.info(f"Queued {len(items)} items for {post.pillar}")
                
                self.last_run["content_generation"] = now
            except Exception as e:
                self.logger.error(f"Error in Content Generation Job: {e}")

    def _check_queue_processing(self, now: datetime):
        job_config = self.config["jobs"].get("queue_processing", {})
        if not job_config.get("enabled", False):
            return
            
        interval = job_config.get("interval_seconds", 60)
        if (now - self.last_run["queue_processing"]) >= timedelta(seconds=interval):
            self.logger.info("Job: Checking Content Queue for ready items...")
            try:
                # Iterate through all platforms to see what can be posted
                platforms = self.posting_rules.config.get("platforms", {}).keys()
                for platform in platforms:
                    dispatch_allowed, block_reason = self.kill_switch_service.is_dispatch_allowed(platform)
                    if not dispatch_allowed:
                        self.logger.info("Skipping dispatch for %s due to %s", platform, block_reason)
                        continue
                    item = self.queue_service.get_next_to_publish(platform)
                    if item:
                        self.logger.info(f"Publishing item {item.id} to {platform}")
                        self._publish_item(item)
                
                self.last_run["queue_processing"] = now
            except Exception as e:
                self.logger.error(f"Error in Queue Processing Job: {e}")

    def _publish_item(self, item):
        try:
            # Check if we have a real connector for this platform
            connector = self.connectors.get(item.platform)
            
            if connector:
                # Implement real dispatch
                # success = connector.post_text(item.content_data["body"])
                # if success:
                #     self.queue_service.mark_as_published(item.id)
                # else:
                #     self.queue_service.mark_as_failed(item.id, "Connector failed to post")
                pass
            else:
                self.logger.warning(f"No connector available for {item.platform}. Simulating success for MVP.")
                self.queue_service.mark_as_published(item.id)
        except Exception as e:
            self.logger.error(f"Failed to publish item {item.id}: {e}")
            self.queue_service.mark_as_failed(item.id, str(e))

    def _check_metrics_collection(self, now: datetime):
        job_config = self.config["jobs"].get("metrics_collection", {})
        if not job_config.get("enabled", False):
            return
            
        interval = job_config.get("interval_hours", 6)
        if (now - self.last_run["metrics_collection"]) >= timedelta(hours=interval):
            self.logger.info("Job: Running Metrics Collection...")
            # Implement metric collection logic (B8/B9)
            self.last_run["metrics_collection"] = now

    def _check_health_monitoring(self, now: datetime):
        job_config = self.config["jobs"].get("health_monitoring", {})
        if not job_config.get("enabled", False):
            return
            
        interval = job_config.get("interval_minutes", 15)
        if (now - self.last_run["health_monitoring"]) >= timedelta(minutes=interval):
            self.logger.info("Job: Running Health Monitoring...")
            alerts = self.health_monitor.run_checks(now=now)
            if alerts:
                self.logger.warning("Health monitoring generated %s alert(s).", len(alerts))
            self.last_run["health_monitoring"] = now

if __name__ == "__main__":
    scheduler = AutonomousSchedulerService(config_path="src/config/scheduler_config.yaml")
    scheduler.start()
