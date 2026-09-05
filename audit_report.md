# Razorpay Agentic Payments / UPI Reserve Pay Audit

## 1. Capability Audit: Is UPI Reserve Pay Enabled?

**Result: UNAVAILABLE / NOT CONFIGURED**

I tested the live Razorpay API credentials against the standard Single Block Multi Debit (SBMD) / TokenHQ order creation parameters required for UPI Reserve Pay (`method: "upi"`, `amount: 0`, with a `token` payload).

*   **Test Result:** The API returned `ERROR: Order amount less than minimum amount allowed`.
*   **Meaning:** Your Razorpay account is **not** currently enabled for ₹0 UPI Mandate/SBMD registration. SBMD / UPI Reserve Pay requires explicit onboarding and feature enablement by the Razorpay team, even in Test Mode, to permit mandate creation without an immediate charge. 

### API Requirements Breakdown
1.  **Agentic Payments API:** Razorpay’s "Agentic Payments" is a product built on top of **UPI Reserve Pay**. Technically, the underlying rail is the NPCI SBMD (Single Block Multi Debit) framework, which maps to Razorpay's TokenHQ (Mandates) API with specific SBMD parameters.
2.  **Mandate/Authorization API:** `POST /orders` with `method: upi` and a `token` object (max_amount, expire_at, frequency: as_presented).
3.  **Debit/Execution API:** `POST /payments/create/recurring` using the generated `token_id` and the customer ID.
4.  **Webhooks:** `token.confirmed` (setup success), `token.rejected` (setup failure), `payment.captured` (debit success), `payment.failed` (debit failure).
5.  **Identifiers:** `token_xxx` represents the UPI Reserve Pay authorization (consent). `pay_xxx` represents the actual money movement (debit).

---

## 2. Code Audit: Current Implementation

The current backend implementation in `app/payment/agentic_service.py` is deeply flawed and heavily simulated.

### Setup Phase (`setup_agentic_authorization`)
*   **The Flaw:** It attempts to call `create_mandate_order` (which currently crashes due to lack of account capability).
*   **The Bigger Flaw:** It stores the returned Razorpay **Order ID** (`order_xxx`) as the `authorization_reference`. This is fundamentally incorrect. An Order ID merely represents the *request* for a mandate. A mandate is only established after the user authenticates via their UPI app, at which point Razorpay issues a **Token ID** (`token_xxx`) via webhook.

### Execution Phase (`execute_agentic_payment` & `execute_direct_agentic_payment`)
*   **`execute_agentic_payment`:** Attempts to execute a recurring payment using the stored `authorization_reference`. Since it stored an Order ID instead of a Token ID, this call will instantly fail on Razorpay's side if it ever runs.
*   **`execute_direct_agentic_payment`:** **Completely simulated.** It generates a fake payment ID (`pay_agentic_xxx`), manually decrements inventory, and forces the payment status to `PAID` without ever communicating with Razorpay.
*   **Missing Webhooks:** The application does not listen for `token.confirmed` or `token.cancelled` webhooks, meaning it has no way to actually know if a user successfully approved or revoked a UPI Reserve Pay block in their banking app.

---

## 3. Separation of Concepts

As requested, these concepts must be strictly separated in our data model:
1.  **Razorpay Order:** The intent to register a mandate or charge an amount (`order_xxx`).
2.  **UPI Reserve Pay Auth:** The actual blocked funds / mandate token (`token_xxx`).
3.  **Actual Payment/Debit:** The transaction deducting funds from the block (`pay_xxx`).
4.  **Internal Agentic Auth:** Our application's `AgenticPaymentAuthorization` record. Its status should remain `PENDING` until a `token.confirmed` webhook attaches the real `token_xxx` to it.

---

## 4. How to Proceed?

Because the API capability is **unavailable** on your current account, we cannot execute a real SBMD/UPI Reserve Pay flow today without Razorpay support. 

Please advise on the path forward:

1.  **Halt & Request Enablement:** Pause agentic payment development until Razorpay Support enables UPI Reserve Pay / SBMD on this account.
2.  **Standard Checkout Fallback:** Remove all fake agentic simulations. When the agent initiates a purchase, it generates a standard Checkout link, requiring the user to manually pay for each transaction until Reserve Pay is enabled.
3.  **Strict TokenHQ Workaround (If Applicable):** If your account allows standard ₹1 authentication mandates (instead of ₹0 SBMD blocks), we could attempt to build the TokenHQ mandate flow, but as you stated, you want *UPI Reserve Pay*. SBMD blocks are the standard for Reserve Pay.
