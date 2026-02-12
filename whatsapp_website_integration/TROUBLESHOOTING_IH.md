# Troubleshooting Guide - IH WhatsApp Integration

## Your System Configuration

Based on your logs, you're using:
- **WhatsApp Module**: IH_Whatsapp_Integration (custom module)
- **Model**: `ih.whatsapp.message`
- **Issue**: Access token expired

## Step-by-Step Fix

### 1. First, Fix Your Access Token (CRITICAL)

Your token expired on: **Monday, 02-Feb-26 05:00:00 PST**

**Fix Now:**
1. Go to **Settings → General Settings → Discuss**
2. Find **WhatsApp Configuration**
3. Generate new token from Meta Business Manager
4. Paste it and **Save**
5. Click **Test Connection**

### 2. Configure the Template

Since you're using IH WhatsApp Integration, configure it like this:

1. **Go to**: Discuss → Configuration → WhatsApp Templates
2. **Create or Edit** your template
3. **Fill in**:
   - **Name**: `order_confirmation` (lowercase, no spaces)
   - **Body**: Your message template
   - **☑️ Auto Send on Website Order**: **CHECK THIS**

### 3. Test the Integration

**Option A: Check Available Models**
Run this in Odoo shell or create a temporary Python snippet:

```python
# Check if IH WhatsApp is available
if 'ih.whatsapp.message' in self.env:
    print("✓ IH WhatsApp Integration found")
    
    # Check available methods
    msg_model = self.env['ih.whatsapp.message']
    methods = [m for m in dir(msg_model) if not m.startswith('_') and 'send' in m.lower()]
    print(f"Available send methods: {methods}")
```

**Option B: Manual Test from Sale Order**
1. Open any confirmed sale order
2. Make sure customer has phone number
3. Click the **WhatsApp** button
4. Check logs immediately

### 4. Check the Logs

Monitor logs in real-time:

```bash
tail -f /var/log/odoo/odoo.log | grep -E "(WhatsApp|whatsapp)"
```

**What to look for:**

✅ **Success looks like:**
```
INFO: Manual WhatsApp send triggered for order SO001
INFO: Found template: order_confirmation
INFO: Sending to phone: +1234567890
INFO: Using IH WhatsApp Integration for order SO001
INFO: Creating IH WhatsApp message for SO001 to +1234567890
INFO: IH WhatsApp message record created with ID: 123
INFO: Calling send_whatsapp_message()
INFO: IH WhatsApp confirmation sent for order SO001 to +1234567890
```

❌ **Failure looks like:**
```
ERROR: WhatsApp API Error: Error validating access token
```

### 5. Common Issues & Fixes

#### Issue 1: "No template found for auto-send"
**Fix:**
- Go to WhatsApp Templates
- Find your template
- Check the "Auto Send on Website Order" checkbox
- Save

#### Issue 2: "No send method found on ih.whatsapp.message"
**Fix:**
This means the IH module's send method name is different. Check the IH module code:

```bash
grep -r "def.*send" /path/to/addons/IH_Whatsapp_Integration/models/
```

Then update the code in `sale_order.py` to use the correct method name.

#### Issue 3: "Customer has no phone"
**Fix:**
- Open the customer record
- Add phone number in **Mobile** or **Phone** field
- Include country code: `+1234567890`

#### Issue 4: Access token expired
**Fix:**
- Generate a **permanent** token using System User in Meta
- Or set up auto-refresh (if supported by IH module)

### 6. Inspect IH WhatsApp Message Model

To understand how to send messages correctly, check the model structure:

```python
# In Odoo shell
msg = self.env['ih.whatsapp.message'].search([], limit=1)
print("Fields:", msg._fields.keys())
print("Methods:", [m for m in dir(msg) if not m.startswith('_')])
```

Common field names:
- `partner_id` - Customer
- `mobile` - Phone number
- `message` - Message body
- `template_id` - Template reference
- `model` - Related model (sale.order)
- `res_id` - Related record ID

### 7. Module Compatibility Check

Check if both modules are installed:

```python
# In Odoo shell
installed = self.env['ir.module.module'].search([
    ('state', '=', 'installed'),
    ('name', 'ilike', 'whatsapp')
])
for mod in installed:
    print(f"{mod.name}: {mod.state}")
```

### 8. Update Module After Changes

After making changes:

```bash
# Restart Odoo
sudo systemctl restart odoo

# Or in development
./odoo-bin -c odoo.conf -u whatsapp_website_integration -d your_database
```

### 9. Debug Mode Template

If still not working, try this debug version:

```python
def action_send_whatsapp_manual(self):
    """Manual action with full debugging"""
    self.ensure_one()
    
    # Check 1: Template
    template = self.env['whatsapp.template'].get_order_confirmation_template()
    _logger.info(f"Template found: {template.name if template else 'None'}")
    
    # Check 2: Phone
    phone = self.partner_id.mobile or self.partner_id.phone
    _logger.info(f"Phone: {phone}")
    
    # Check 3: Model availability
    _logger.info(f"ih.whatsapp.message available: {'ih.whatsapp.message' in self.env}")
    
    # Check 4: Create test message
    if 'ih.whatsapp.message' in self.env:
        test_msg = self.env['ih.whatsapp.message'].create({
            'partner_id': self.partner_id.id,
            'mobile': phone,
            'message': 'Test message from Odoo',
        })
        _logger.info(f"Test message created: {test_msg.id}")
        
        # List all methods
        methods = [m for m in dir(test_msg) if 'send' in m.lower()]
        _logger.info(f"Available methods: {methods}")
```

### 10. Check IH WhatsApp Settings

The IH WhatsApp Integration module likely has its own settings:

1. Go to **Settings**
2. Look for **IH WhatsApp** section
3. Check:
   - API credentials
   - Access token
   - Phone number ID
   - Business account ID

## Expected Behavior

**Automatic:**
1. Customer places order on website → Pays → Order confirmed
2. Module detects it's a website order
3. Checks if template has "Auto Send" enabled
4. Creates WhatsApp message record
5. Sends message to customer
6. Marks order as `whatsapp_msg_sent = True`

**Manual:**
1. Open sale order
2. Click WhatsApp button
3. Message sent immediately
4. Notification appears

## Still Not Working?

Run this complete diagnostic:

```python
# Complete diagnostic script
order = self.env['sale.order'].browse(YOUR_ORDER_ID)

print("=== DIAGNOSTIC ===")
print(f"Order: {order.name}")
print(f"Customer: {order.partner_id.name}")
print(f"Phone: {order.partner_id.mobile or order.partner_id.phone}")
print(f"Website Order: {bool(order.website_id)}")
print(f"Message Sent: {order.whatsapp_msg_sent}")

# Check template
template = self.env['whatsapp.template'].search([
    ('auto_send_on_order', '=', True)
], limit=1)
print(f"Auto-send template: {template.name if template else 'None'}")

# Check model
print(f"IH WhatsApp available: {'ih.whatsapp.message' in self.env}")

# Try to get recent WhatsApp messages
if 'ih.whatsapp.message' in self.env:
    recent = self.env['ih.whatsapp.message'].search([
        ('model', '=', 'sale.order'),
        ('res_id', '=', order.id)
    ])
    print(f"WhatsApp messages for this order: {len(recent)}")
    for msg in recent:
        print(f"  - ID: {msg.id}, Mobile: {msg.mobile}, Sent: {msg.state if hasattr(msg, 'state') else 'unknown'}")
```

Share the output and I can help you fix the specific issue!
