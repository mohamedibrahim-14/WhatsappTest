# Meta Conversions API Integration (Odoo 17)

This module integrates Odoo with **Meta (Facebook) Conversions API** so you can send
server-side events (e.g. PageView, AddToCart, Purchase) from your website and
business flows.

It is designed to work alongside your existing **Meta Pixel** module
(`ih-meta-integration`), providing a more reliable and privacy-friendly
tracking channel.

---

## 1. Requirements on Meta (Facebook) side

1. Go to **Meta Events Manager** for your Business account.
2. Select the **Pixel** that you already use for the website.
3. In the **Settings** tab:
   - Enable **Conversions API**.
   - Create a **System User** and generate a **Permanent Access Token** (or another
     suitable access token) with the required permissions.
4. (Optional but recommended) Create a **Test Event Code** for validating events
   in Events Manager.

You will need:

- Pixel ID
- Conversions API Access Token
- (Optional) Test Event Code

---

## 2. Install the module in Odoo

1. Ensure the folder is available in your Odoo addons path:

   - `odoo/custom_addons/ih_meta_conversions_api`

2. Restart the Odoo server so it discovers the new module.
3. In Odoo, go to **Apps**:
   - Activate **Developer Mode** if needed.
   - Click **Update Apps List**.
   - Search for **"Meta Conversions API Integration"**.
   - Install the module.

---

## 3. Configure in Odoo Website Settings

1. In Odoo, go to:

   - **Website → Configuration → Settings**

2. Look for the **Meta Conversions API** box (near the CDN / SEO settings).
3. Enable **"Meta Conversions API"**.
4. Fill in:
   - **Meta Pixel ID**: the same Pixel used by your existing Meta Pixel integration.
   - **Meta Conversions API Access Token**: the access token generated in Events Manager.
   - **Test Event Code** (optional): used while testing events in Events Manager.
5. Click **Save**.

The configuration uses **System Parameters**:

- `meta_capi.enabled`
- `meta_capi.pixel_id`
- `meta_capi.access_token`
- `meta_capi.test_event_code`

You can view/edit them under **Settings → Technical → Parameters → System Parameters**
if you have technical rights.

---

## 4. How to send events from Odoo

This module provides a helper model: `meta.conversions.api`.

You can call it from:

- Python code in your custom modules.
- **Server Actions** (Python code) to hook into events like order confirmation.

### 4.1. Basic example (Server Action on `sale.order`)

1. Go to **Settings → Technical → Automation → Server Actions**.
2. Create a new action:
   - **Action Name**: `Send Meta CAPI Purchase`
   - **Model**: `Sales Order`
   - **Action To Do**: `Execute Python Code`
3. Use code similar to:

```python
meta_api = env["meta.conversions.api"]

for order in records:
    custom_data = {
        "currency": order.currency_id.name,
        "value": float(order.amount_total),
        "content_ids": [line.product_id.id for line in order.order_line],
        "content_type": "product",
    }

    # You can pass additional user_data fields if you have them (hashed email, etc.)
    user_data = {
        # "em": "<sha256_of_customer_email>",
        # "ph": "<sha256_of_customer_phone>",
    }

    meta_api.send_event(
        event_name="Purchase",
        user_data=user_data,
        custom_data=custom_data,
    )
```

4. Link this server action to an automated action or button, for example:
   - Trigger **On Update** of `sale.order` when state becomes `sale`/`done`.

### 4.2. Custom events

You can send any event name that Meta supports, for example:

- `PageView`
- `AddToCart`
- `InitiateCheckout`
- `Purchase`

Example from custom code:

```python
import hashlib

def hash_norm(value):
    v = (value or "").strip().lower()
    return hashlib.sha256(v.encode("utf-8")).hexdigest() if v else ""

user_data = {
    "em": hash_norm("test@example.com"),  # replace with a real email for better matching
}

env["meta.conversions.api"].send_event(
    event_name="AddToCart",
    user_data=user_data,
    custom_data={
        "currency": "USD",
        "value": 25.0,
        "content_ids": [product.id],
        "content_type": "product",
    },
)
```

---

## 5. Testing and validation

1. In Meta **Events Manager**, select the Pixel.
2. Go to the **Test Events** tab.
3. Copy the **Test Event Code** and paste it in:
   - **Website → Configuration → Settings → Meta Conversions API → Test Event Code**
4. Trigger your test event from Odoo (e.g., confirm a Sales Order or run a Server Action).
5. You should see the event appearing in the Test Events panel.

Once you are satisfied that events work, you can:

- Clear the Test Event Code (to send real production events),
- Or leave it empty in the Odoo settings and let Meta treat them as normal events.

---

## 6. Working together with Meta Pixel (client-side)

Your existing module `ih-meta-integration` injects the **Meta Pixel** script on the website
and tracks events like `PageView`, `AddToCart`, and `Purchase` in the browser.

With this new module:

- You can send the **same events server-side** using Conversions API.
- For best deduplication, you can provide an `event_id` both in the Pixel JavaScript
  and in the `send_event` calls. (This is optional and can be added later.)

---

## 7. Notes & recommendations

- Always respect local laws and your privacy policy when tracking users.
- For user_data (email, phone, etc.), Meta requires values to be normalized and
  **SHA256 hashed**; make sure to apply this in your custom code before sending.
- If you see HTTP errors, check the Odoo logs: errors from Meta Conversions API
  are logged with the logger name `meta.conversions.api`.

