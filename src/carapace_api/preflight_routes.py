"""Bank-authenticated preflight API and deterministic risk policy."""

from __future__ import annotations

import base64
import binascii
import hashlib
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Literal
from uuid import uuid4

from cryptography.exceptions import UnsupportedAlgorithm
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from carapace_ai.provider import LensIntentProvider
from carapace_ai.redaction import redact_for_model
from carapace_core.bank_envelope import BankEnvelopeSigner
from carapace_core.canonical import canonical_json, sha256_hex
from carapace_core.device_ack import build_device_statement
from carapace_core.lens import IntentDirection, MessageIntent
from carapace_core.protection_proof import verify_protection_bundle

from .auth import TenantAuthenticator, TenantContext
from .preflight import PreflightConflict, PreflightGate, PreflightNotFound
from .preflight_evidence import EvidenceIntegrityError, EvidenceNotFound, PreflightEvidenceLog


class CreatePaymentOrder(BaseModel):
    payer_account: str = Field(pattern=r"^[0-9]{10}$")
    payee_account: str = Field(pattern=r"^[0-9]{10}$")
    payee_display_name: str = Field(min_length=2, max_length=120)
    amount_minor: int = Field(gt=0, le=100_000_000)
    currency: Literal["INR"] = "INR"
    reference: str = Field(min_length=1, max_length=100)
    expires_in_seconds: int = Field(default=600, ge=30, le=900)


class EvaluatePaymentOrder(BaseModel):
    context_text: str = Field(default="", max_length=4000)
    image_base64: str | None = Field(default=None, max_length=3_000_000)
    image_mime_type: Literal["image/png", "image/jpeg", "image/webp"] | None = None
    locale: str = Field(default="en-IN", max_length=20)


class SubmitPaymentOrder(BaseModel):
    decision_id: str = Field(min_length=8, max_length=80)


class RegisterTestDevice(BaseModel):
    payer_account: str = Field(pattern=r"^[0-9]{10}$")
    device_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")
    public_key_spki_base64: str = Field(min_length=80, max_length=500)


class AcknowledgePaymentOrder(BaseModel):
    device_id: str = Field(pattern=r"^[A-Za-z0-9_-]{8,80}$")
    choice: Literal["PROCEED", "CANCEL"]
    statement_json: str = Field(min_length=100, max_length=6000)
    signature_base64: str = Field(min_length=80, max_length=120)


def _normal(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _visible_amounts_minor(text: str) -> set[int]:
    values: set[int] = set()
    for match in re.finditer(r"(?:₹|inr\s*|rs\.?\s*)([0-9][0-9,]{0,12}(?:\.[0-9]{1,2})?)", text, re.IGNORECASE):
        try:
            values.add(int(Decimal(match.group(1).replace(",", "")) * 100))
        except InvalidOperation:
            continue
    return values


def _decide(
    intent: MessageIntent, context_text: str, has_image: bool, envelope: dict[str, Any]
) -> tuple[str, list[str]]:
    source = _normal(context_text)
    visible_amounts = _visible_amounts_minor(context_text)
    reasons: list[str] = []
    warnings: list[str] = []
    if any(term in source for term in ("refund", "cashback", "receive money", "money back", "credited to you")):
        reasons.append("TEXT_PROMISES_RECEIPT_BUT_ORDER_SENDS")
    span_grounded = bool(intent.evidence_span and _normal(intent.evidence_span) in source)
    if intent.expected_direction == IntentDirection.RECEIVE_EXPECTED:
        if span_grounded:
            reasons.append("GROUNDED_RECEIVE_VS_SEND")
        else:
            warnings.append("AI_IMAGE_RECEIVE_SIGNAL_UNCONFIRMED" if has_image else "AI_RECEIVE_SIGNAL_UNCONFIRMED")
    if intent.asks_for_pin_to_receive:
        if "pin" in source and any(term in source for term in ("refund", "receive", "cashback")):
            reasons.append("PIN_TO_RECEIVE_WARNING")
        else:
            warnings.append("AI_PIN_SIGNAL_UNCONFIRMED")
    if intent.expected_amount_minor is not None and intent.expected_amount_minor != envelope["amount_minor"]:
        if intent.expected_amount_minor in visible_amounts:
            reasons.append("GROUNDED_AMOUNT_MISMATCH")
        else:
            warnings.append("AI_AMOUNT_MISMATCH_UNCONFIRMED")
    bank_payee = _normal(envelope["payee_display_name"])
    claimed_payee = _normal(intent.claimed_entity or "")
    if claimed_payee and claimed_payee in source and bank_payee not in source:
        reasons.append("CLAIMED_PAYEE_DIFFERS_FROM_BANK_PAYEE")
    elif bank_payee not in source:
        warnings.append("BANK_PAYEE_NOT_ESTABLISHED_IN_CONTEXT")
    if reasons:
        return "HOLD", sorted(set(reasons))
    if not source and has_image:
        return "WARN", ["IMAGE_TEXT_NOT_INDEPENDENTLY_GROUNDED"]
    if warnings:
        return "WARN", warnings
    if intent.expected_direction != IntentDirection.SEND:
        return "WARN", ["PAYMENT_PURPOSE_UNCLEAR"]
    if intent.expected_amount_minor is None:
        return "WARN", ["PAYMENT_AMOUNT_NOT_ESTABLISHED"]
    if intent.expected_amount_minor not in visible_amounts:
        return "WARN", ["PAYMENT_AMOUNT_NOT_IN_CONTEXT_TEXT"]
    if intent.evidence_span and not span_grounded:
        return "WARN", ["AI_EVIDENCE_SPAN_NOT_GROUNDED"]
    return "ALLOW", ["NO_INTENT_CONTRADICTION_FOUND"]


def register_preflight_routes(
    application: FastAPI,
    *,
    authenticate: TenantAuthenticator,
    gate: PreflightGate,
    signer: BankEnvelopeSigner,
    witness_signer: BankEnvelopeSigner,
    evidence_log: PreflightEvidenceLog,
    provider: LensIntentProvider,
) -> None:
    def verify_decision(value: dict[str, Any]) -> bool:
        signature = value.pop("bank_signature", None)
        try:
            return isinstance(signature, str) and signer.verify(value, signature)
        finally:
            if signature is not None:
                value["bank_signature"] = signature

    def load_verified(tenant_id: str, order_id: str) -> dict[str, Any]:
        try:
            saved = gate.get_order(tenant_id, order_id)
        except PreflightNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        envelope = saved["envelope"]
        if not signer.verify(envelope, saved["bank_signature"]):
            raise HTTPException(status_code=409, detail="bank payment signature is invalid")
        if envelope["tenant_id"] != tenant_id:
            raise HTTPException(status_code=409, detail="bank identity mismatch")
        return saved

    @application.post("/v1/preflight/devices", status_code=201, tags=["preflight"])
    async def register_test_device(
        request: RegisterTestDevice, tenant: TenantContext = Depends(authenticate)
    ) -> dict[str, Any]:
        try:
            registered = await run_in_threadpool(
                gate.register_device, tenant.tenant_id, request.payer_account,
                request.device_id, request.public_key_spki_base64,
            )
        except (ValueError, binascii.Error, UnsupportedAlgorithm) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except PreflightConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        return {
            **registered,
            "enrolment_scope": "Bank-authenticated local test enrollment; not production customer identity verification.",
        }

    @application.post("/v1/preflight/orders", status_code=201, tags=["preflight"])
    async def create_order(
        request: CreatePaymentOrder, tenant: TenantContext = Depends(authenticate)
    ) -> dict[str, Any]:
        if request.payer_account == request.payee_account:
            raise HTTPException(status_code=422, detail="payer and payee must differ")
        now = datetime.now(timezone.utc)
        envelope = {
            "schema_version": "preflight-1",
            "tenant_id": tenant.tenant_id,
            "order_id": f"order_{uuid4().hex}",
            "payer_account": request.payer_account,
            "payee_account": request.payee_account,
            "payee_display_name": request.payee_display_name,
            "amount_minor": request.amount_minor,
            "currency": request.currency,
            "direction": "SEND",
            "reference": request.reference,
            "nonce": uuid4().hex,
            "policy_version": "intent-gate-1",
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(seconds=request.expires_in_seconds)).isoformat(),
        }
        signature = signer.sign(envelope)
        gate.put_order(tenant.tenant_id, envelope, signature)
        return {"envelope": envelope, "bank_signature": signature, "key_id": signer.key_id}

    @application.get("/v1/preflight/orders/{order_id}", tags=["preflight"])
    async def get_order(
        order_id: str, tenant: TenantContext = Depends(authenticate)
    ) -> dict[str, Any]:
        return load_verified(tenant.tenant_id, order_id)

    @application.post("/v1/preflight/orders/{order_id}/evaluate", tags=["preflight"])
    async def evaluate_order(
        order_id: str,
        request: EvaluatePaymentOrder,
        tenant: TenantContext = Depends(authenticate),
    ) -> dict[str, Any]:
        saved = load_verified(tenant.tenant_id, order_id)
        if saved["decision"] is not None:
            raise HTTPException(status_code=409, detail="order already evaluated")
        if datetime.fromisoformat(saved["envelope"]["expires_at"]) <= datetime.now(timezone.utc):
            raise HTTPException(status_code=409, detail="payment order expired")
        if not request.context_text.strip() and request.image_base64 is None:
            raise HTTPException(status_code=422, detail="supply payment context text or a screenshot")
        image_bytes: bytes | None = None
        if request.image_base64 is not None:
            if request.image_mime_type is None:
                raise HTTPException(status_code=422, detail="screenshot MIME type is required")
            try:
                image_bytes = base64.b64decode(request.image_base64, validate=True)
            except (ValueError, binascii.Error) as error:
                raise HTTPException(status_code=422, detail="invalid screenshot encoding") from error
            if len(image_bytes) == 0 or len(image_bytes) > 2_000_000:
                raise HTTPException(status_code=422, detail="screenshot size must be 1–2 MB")
            looks_like_image = (
                (request.image_mime_type == "image/png" and image_bytes.startswith(b"\x89PNG\r\n\x1a\n"))
                or (request.image_mime_type == "image/jpeg" and image_bytes.startswith(b"\xff\xd8\xff"))
                or (request.image_mime_type == "image/webp" and image_bytes.startswith(b"RIFF") and image_bytes[8:12] == b"WEBP")
            )
            if not looks_like_image:
                raise HTTPException(status_code=422, detail="screenshot bytes do not match MIME type")
        cleaned = redact_for_model(request.context_text)
        provider_error = False
        provider_error_type: str | None = None
        try:
            if image_bytes is None:
                intent = await run_in_threadpool(provider.extract_intent, cleaned.text, request.locale)
            else:
                intent = await run_in_threadpool(
                    provider.extract_intent_from_image,
                    image_bytes, request.image_mime_type, cleaned.text, request.locale,
                )
        except Exception as error:
            provider_error = True
            provider_error_type = type(error).__name__
            intent = None
        if provider_error or intent is None:
            verdict, reasons = "HOLD", ["CONTEXT_ANALYSIS_UNAVAILABLE"]
        else:
            verdict, reasons = _decide(
                intent, cleaned.text, image_bytes is not None, saved["envelope"]
            )
        decision: dict[str, Any] = {
            "decision_id": f"decision_{uuid4().hex}",
            "order_id": order_id,
            "verdict": verdict,
            "reason_codes": reasons,
            "customer_message": (
                "This context suggests money will come to you, but the bank order will send money. This test payment was stopped."
                if verdict == "HOLD" and any("RECEIPT" in code or "RECEIVE" in code for code in reasons)
                else "This payment cannot continue until the concern is reviewed."
                if verdict == "HOLD"
                else "The context is incomplete or unverified. This test payment is paused."
                if verdict == "WARN"
                else "No supported contradiction was found. This synthetic test payment may proceed."
            ),
            "provider_mode": provider.mode,
            "model": provider.model_name,
            "live_model_called": provider.mode in {"GEMINI_API", "VERTEX_AI"} and not provider_error,
            "provider_error_type": provider_error_type,
            "image_supplied": image_bytes is not None,
            "input_redaction_applied": cleaned.redaction_applied,
            "envelope_signature": saved["bank_signature"],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "protection_receipt_id": f"protection_{uuid4().hex}",
        }
        decision["bank_signature"] = signer.sign(decision)
        receipt = {
            "schema_version": "carapace-protection-1",
            "receipt_id": decision["protection_receipt_id"],
            "stage": "DECISION",
            "tenant_id": tenant.tenant_id,
            "order_id": order_id,
            "decision_id": decision["decision_id"],
            "bank_order_digest": sha256_hex(saved["envelope"]),
            "bank_order_signature": saved["bank_signature"],
            "amount_minor": saved["envelope"]["amount_minor"],
            "currency": saved["envelope"]["currency"],
            "direction": saved["envelope"]["direction"],
            "bank_payee": saved["envelope"]["payee_display_name"],
            "bank_payee_account_last4": saved["envelope"]["payee_account"][-4:],
            "verdict": verdict,
            "reason_codes": reasons,
            "issued_warning": decision["customer_message"],
            "provider_mode": provider.mode,
            "model": provider.model_name,
            "live_model_called": decision["live_model_called"],
            "context_sha256": hashlib.sha256(request.context_text.encode("utf-8")).hexdigest(),
            "image_sha256": hashlib.sha256(image_bytes).hexdigest() if image_bytes else None,
            "issued_at": decision["created_at"],
            "acknowledgement_state": "NOT_ACKNOWLEDGED",
            "claim_limit": "Bank-issued warning only; no proof the customer saw or understood it.",
        }
        try:
            bundle = gate.put_decision(
                tenant.tenant_id, order_id, decision, receipt=receipt,
                evidence_log=evidence_log, bank_signer=signer,
            )
        except PreflightConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except EvidenceIntegrityError as error:
            raise HTTPException(status_code=503, detail="protection evidence is unavailable") from error
        return {**decision, "protection_bundle": bundle}

    @application.get(
        "/v1/preflight/orders/{order_id}/acknowledgement-challenge", tags=["preflight"]
    )
    async def acknowledgement_challenge(
        order_id: str,
        device_id: str = Query(pattern=r"^[A-Za-z0-9_-]{8,80}$"),
        choice: Literal["PROCEED", "CANCEL"] = Query(),
        tenant: TenantContext = Depends(authenticate),
    ) -> dict[str, Any]:
        saved = load_verified(tenant.tenant_id, order_id)
        envelope, decision = saved["envelope"], saved["decision"]
        if decision is None or not verify_decision(decision):
            raise HTTPException(status_code=409, detail="signed preflight decision is unavailable")
        if decision["order_id"] != order_id or decision["envelope_signature"] != saved["bank_signature"]:
            raise HTTPException(status_code=409, detail="decision does not bind this payment")
        if datetime.fromisoformat(envelope["expires_at"]) <= datetime.now(timezone.utc):
            raise HTTPException(status_code=409, detail="payment order expired")
        if decision["verdict"] == "HOLD" and choice == "PROCEED":
            raise HTTPException(status_code=409, detail="HOLD cannot be overridden by customer choice")
        try:
            device = gate.get_device(tenant.tenant_id, envelope["payer_account"], device_id)
        except PreflightNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        statement = build_device_statement(
            envelope, decision, choice=choice, device_id=device_id,
            device_key_sha256=device["device_key_sha256"],
        )
        return {
            "statement_json": canonical_json(statement),
            "statement": statement,
            "scope": "Signature proves key control over these bytes, not that a human saw or understood them.",
        }

    @application.post("/v1/preflight/orders/{order_id}/acknowledge", tags=["preflight"])
    async def acknowledge_order(
        order_id: str,
        request: AcknowledgePaymentOrder,
        tenant: TenantContext = Depends(authenticate),
    ) -> dict[str, Any]:
        try:
            bundle = await run_in_threadpool(
                gate.put_acknowledgement,
                tenant.tenant_id, order_id,
                device_id=request.device_id, choice=request.choice,
                statement_json=request.statement_json,
                device_signature_base64=request.signature_base64,
                now=datetime.now(timezone.utc),
                verify_envelope=signer.verify, verify_decision=verify_decision,
                evidence_log=evidence_log, bank_signer=signer,
            )
        except PreflightNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PreflightConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except EvidenceIntegrityError as error:
            raise HTTPException(status_code=503, detail="protection evidence is unavailable") from error
        return {"choice_recorded": request.choice, "protection_bundle": bundle}

    @application.post("/v1/preflight/orders/{order_id}/submit", tags=["preflight"])
    async def submit_order(
        order_id: str,
        request: SubmitPaymentOrder,
        tenant: TenantContext = Depends(authenticate),
    ) -> dict[str, Any]:
        try:
            transfer, bundle = await run_in_threadpool(
                gate.submit, tenant.tenant_id, order_id, request.decision_id,
                f"synthetic_{uuid4().hex}",
                now=datetime.now(timezone.utc),
                verify_envelope=signer.verify,
                verify_decision=verify_decision,
                evidence_log=evidence_log,
                bank_signer=signer,
            )
        except PreflightNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except PreflightConflict as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except EvidenceIntegrityError as error:
            raise HTTPException(status_code=503, detail="protection evidence is unavailable") from error
        return {"status": "POSTED_SYNTHETIC", "transfer": transfer, "protection_bundle": bundle}

    @application.get("/v1/preflight/receipts/{receipt_id}", tags=["preflight"])
    async def get_protection_receipt(
        receipt_id: str, tenant: TenantContext = Depends(authenticate)
    ) -> dict[str, Any]:
        try:
            bundle = await run_in_threadpool(evidence_log.get_bundle, tenant.tenant_id, receipt_id)
        except EvidenceNotFound as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except EvidenceIntegrityError as error:
            raise HTTPException(status_code=503, detail="protection evidence is unavailable") from error
        return {
            "bundle": bundle,
            "local_proof_verified": verify_protection_bundle(
                bundle, bank_public_key=signer.public_key_bytes,
                witness_public_key=witness_signer.public_key_bytes,
            ),
            "verification_scope": "Same-operator local keys; external verifier must pin public keys independently.",
        }

    @application.get("/v1/preflight/public-keys", tags=["preflight"])
    async def get_protection_public_keys(
        tenant: TenantContext = Depends(authenticate)
    ) -> dict[str, Any]:
        del tenant
        return {
            "bank": {"key_id": signer.key_id, "ed25519_public_key_base64": base64.b64encode(signer.public_key_bytes).decode()},
            "witness": {"key_id": witness_signer.key_id, "ed25519_public_key_base64": base64.b64encode(witness_signer.public_key_bytes).decode()},
            "warning": "Pin these keys through an independent channel before trusting a disclosed receipt.",
        }

    @application.get("/v1/preflight/transfers", tags=["preflight"])
    async def list_transfers(tenant: TenantContext = Depends(authenticate)) -> dict[str, Any]:
        return {"ledger": "CARAPACE_LOCAL_SYNTHETIC", "transfers": gate.list_transfers(tenant.tenant_id)}
