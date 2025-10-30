from fastapi import FastAPI
from fastapi.testclient import TestClient
from endpoints.payment_handler import router as payment_router


def make_app():
    app = FastAPI()
    app.include_router(payment_router)
    return app


def test_trigger_payment_collection_returns_pay_twiml(monkeypatch):
    # Fake subscription manager to simulate no active subscription
    async def fake_get_subscription_manager():
        class FakeMgr:
            async def check_active_subscription(self, phone):
                return {"active": False}
        return FakeMgr()

    monkeypatch.setattr("endpoints.payment_handler.get_subscription_manager", fake_get_subscription_manager)

    app = make_app()
    client = TestClient(app)
    resp = client.post("/payment/trigger", data={"From": "+447700900123", "CallSid": "CSID123"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/xml")
    body = resp.text
    assert "<Pay" in body
    assert "charge_amount\">6.00" in body or "charge_amount=\"6.00\"" in body


def test_payment_complete_success_monkeypatched(monkeypatch):
    # Patch Stripe charge creation to avoid network
    class Charge:
        id = "ch_test_123"

    def fake_charge_create(**kwargs):
        # Ensure idempotency_key is passed
        assert "idempotency_key" in kwargs
        return Charge()

    # monkeypatch run_in_threadpool path by patching stripe.Charge.create directly (the call is wrapped)
    import endpoints.payment_handler as ph
    monkeypatch.setattr(ph.stripe.Charge, "create", staticmethod(fake_charge_create))

    # Fake subscription manager
    async def fake_get_subscription_manager():
        class FakeMgr:
            def _hash_phone(self, p):
                return "hash"

            async def create_subscription(self, phone, payment_id, minutes):
                return None
        return FakeMgr()

    monkeypatch.setattr("endpoints.payment_handler.get_subscription_manager", fake_get_subscription_manager)

    # Fake conversation logger
    class FakeLogger:
        async def log_payment(self, **kwargs):
            return None

    async def fake_get_conversation_logger():
        return FakeLogger()

    monkeypatch.setattr("endpoints.payment_handler.get_conversation_logger", fake_get_conversation_logger)

    app = make_app()
    client = TestClient(app)
    resp = client.post(
        "/payment/complete",
        data={
            "From": "+447700900123",
            "CallSid": "CSID456",
            "Result": "success",
            "PaymentToken": "tok_test_123",
        },
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/xml")
    assert "payment received" in resp.text.lower()
