# VERSION HISTORY v1.1.0 · 2026-09-02 · Advertise implemented participant gateway and successful delivery charging.
# v1.0.0 · 2026-09-02 · Document successful result retrieval and refreshed-answer receipt semantics.
from .config import Settings
from .contracts import QueryDelivery, QueryRequest


def contract(settings: Settings) -> dict:
    return {
        'mode': settings.intelligence_mode,
        'provider_url': settings.intelligence_url,
        'query_schema': QueryRequest.model_json_schema(),
        'delivery_schema': QueryDelivery.model_json_schema(),
        'fee_usd': str(settings.intelligence_fee),
        'delivery_definition': 'Successful authorised retrieval of a durable result receipt; not proof a model read it.',
        'identity': 'Authenticated actor + request_id + revision. Same identity with changed content is a conflict.',
        'exact_retry': 'Recover the same receipt/result without another fee, including after response loss.',
        'refresh': 'Increase revision for a new result receipt. Successful delivery incurs a new fee even if selected strategies coincide.',
        'provider_failure': 'No successful receipt, no intelligence fee.',
        'simulation': 'Random strategy selection only. Query kind/window are preserved but not analytically evaluated.',
        'charging_implemented': True,
        'visitor_query_url': '/participant/v1/me/queries',
        'visitor_receipt_url': '/participant/v1/me/queries/{delivery_id}',
    }
