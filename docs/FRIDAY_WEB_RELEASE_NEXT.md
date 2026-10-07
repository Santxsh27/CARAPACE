# Friday cloud website — next release gate

Updated October 8, 2026. The owner has completed real Google sign-in through IAP. This remains an invited artificial-money pilot, not a production banking release.

## Code added

- `src/carapace_integrations/friday_cloud_web.py`: FastAPI gateway for the invited artificial-money pilot.
- `tests/test_friday_cloud_web.py`: 16 tests for identity rejection, exact audience/issuer enforcement, tenant isolation, same-origin mutation requests, route restrictions, upload limits, credential acquisition failure, no automatic POST retries, uncached authentication errors, configuration validation and cloud HTML control removal.
- `Dockerfile.web`: a small gateway layer over the immutable verified API image; no dependency reinstall and no secrets included.

The gateway verifies IAP's signed JWT using Google's verifier, exact audience and issuer. Browser-provided tenant/API-key headers are ignored. The server maps the verified email to an enrolled tenant and acquires its own Google identity token to call the private backend. Keys never enter HTML or browser storage. Payment POSTs are never automatically retried by the proxy; timeouts explicitly warn that the outcome may be unknown.

The cloud page excludes legacy labs and local-only inbox monitoring. Continuous Cloud Tasks monitoring remains a separate milestone. This invited-user pilot is not open consumer registration.

## Verification — October 8

The source and test folders are downloaded. Full isolated Docker suite with the saved gateway modules: **175 tests in 75.296 seconds, OK (one optional Anthos integration test skipped)**. The original 11 gateway checks also passed before the additional five regression tests were added.

The mock identity tests exercise rejection and SDK invocation boundaries; they do not establish real cryptographic login. Separately, the owner completed real Google login: the browser loaded the protected page, Gemini readiness, cloud journal status, scenarios and mandate through the private gateway. The browser published a fresh ₹2,487 test-provider bill successfully (gateway POST HTTP 200). Full payment and safety outcome evidence is recorded in `FRIDAY_BROWSER_VERIFICATION_1008.md`. Initial disk space was about 2.4 GiB, so the website build used a tiny source context and reused the immutable cloud image.

## Deployment sequence after tests

1. Full suite passed. Check browser initialization after the monitoring section is excluded.
2. Build a clean image containing this gateway; leave the verified API revision unchanged.
3. Create a separate web service identity. Grant only Cloud Run invoker on the private Friday API and access to the named tenant credential secret. Do not grant the web identity Vertex or Firestore access.
4. Deploy `financial-friday-web` privately, with minimum instances 0 and maximum 2. Entrypoint: `python -m carapace_integrations.friday_cloud_web`.
5. Configure Google IAP and its OAuth client. A personal/no-organization project needs the one-time custom OAuth setup; use the Cloud Run console's IAP configuration. Do not publish an unprotected credentialed proxy.
6. Grant invited accounts IAP access. Initially enroll only the owner; teammates/judges need explicit enrollment and separate tenant credentials. No shared consumer tenant.
7. Verify Google login, rejected unenrolled identity, two-user isolation, fresh bill execution, repeat confirmation, document handling, cross-origin rejection and private API IAM. Only then publish the protected website link.

## Required gateway environment

Cloud image build succeeded: `7863d2c4-4c83-4547-a1ba-04f91834e40a`.
Immutable website image: `asia-south1-docker.pkg.dev/project-70f2c2d7-4e72-4e59-b14/financial-friday/web@sha256:2a6d53f6d9be3e2f728a8c43aa00e4bc5f1907b2b9563693e1c98c86dfbeba2d`.
The generated cloud HTML JavaScript passed Node's syntax check. This is not a browser rendering or authenticated end-to-end test.

## Deployed staging status

- Service: `financial-friday-web`, Mumbai, final UI revision `financial-friday-web-journey1008`. Current image and browser evidence: `FRIDAY_BROWSER_VERIFICATION_1008.md`; the earlier gateway image above is retained as historical deployment evidence.
- Origin: `https://financial-friday-web-171681243260.asia-south1.run.app`; same-origin protection is bound to this actual deployment URL.
- Runtime: `financial-friday-web@project-70f2c2d7-4e72-4e59-b14.iam.gserviceaccount.com`, granted only invocation of the Friday API and access to the named tenant credential secret. No Vertex/Firestore roles were granted to this identity.
- Minimum instances 0, maximum 2; CPU 1, memory 256 MiB, concurrency 8, request timeout 180 seconds.
- Authenticated Cloud Run proxy check: `/health` HTTP 200; `/` without a signed IAP assertion HTTP 401, `Google sign-in required`.
- Google IAP and project-level custom OAuth are configured. The consent app is External/Testing. Only the owner is enrolled in the web service's IAP access policy and tenant mapping. No anonymous access was added.
- Teammates and judges still need explicitly approved, separately enrolled identities and tenant mappings before they can use the demo. Do not enable unauthenticated access or share the owner's credentials.

```text
FRIDAY_WEB_BACKEND_URL=https://financial-friday-api-apl5povwtq-el.a.run.app
FRIDAY_WEB_ORIGIN=<actual HTTPS web service origin>
FRIDAY_WEB_IAP_AUDIENCE=/projects/171681243260/locations/asia-south1/services/financial-friday-web
FRIDAY_WEB_USERS_JSON=<server-side JSON mapping invited emails to distinct enrolled tenant IDs>
CARAPACE_TENANT_KEYS_JSON=<Secret Manager mounted environment value; never print or commit>
PORT=8080
```

Verify the exact audience and service origin from the deployed resource; do not guess either. An API key is not Google login, and IAP deployment protection is not a production consumer identity/onboarding solution.

## Official references

- [IAP for Cloud Run](https://docs.cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run)
- [Verify signed IAP headers](https://docs.cloud.google.com/iap/docs/signed-headers-howto)
- [Private service-to-service authentication](https://docs.cloud.google.com/run/docs/authenticating/service-to-service)
