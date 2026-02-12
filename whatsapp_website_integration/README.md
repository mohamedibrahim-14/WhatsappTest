# WhatsApp Website Order Confirmation Module

## Overview
This module extends Odoo 17's WhatsApp integration to automatically send confirmation messages to customers when they place orders through your website.

## Features
- ✅ Automatic WhatsApp notifications on website order confirmation
- ✅ New "Auto Send on Website Order" field in WhatsApp templates
- ✅ Support for multiple templates with easy selection
- ✅ Tracks whether confirmation message has been sent
- ✅ Integrates with payment transactions
- ✅ Error handling and logging

## Prerequisites
1. Odoo 17 installed
2. WhatsApp module installed and configured
3. WhatsApp Business API account set up
4. Approved WhatsApp message templates

## Installation

### Step 1: Copy Module to Addons
```bash
cp -r whatsapp_website_integration /path/to/odoo/addons/
```

### Step 2: Update Apps List
1. Go to Apps menu
2. Click "Update Apps List"
3. Search for "WhatsApp Website Order Confirmation"
4. Click Install

## Configuration

### Step 1: Create WhatsApp Template in Meta Business Manager
1. Go to Meta Business Manager (https://business.facebook.com/)
2. Navigate to WhatsApp Manager
3. Go to Message Templates
4. Click "Create Template"
5. Use this example template:

**Template Name:** `order_confirmation`
**Category:** Transactional
**Language:** Your language (e.g., English)

**Template Body:**
```
Hello {{1}},

Thank you for your order {{2}}!

Your order has been confirmed and is being processed.

Order Total: {{3}}

We will notify you once your order is ready for delivery.

Thank you for shopping with us!
```

**Variables:**
- {{1}} = Customer Name
- {{2}} = Order Number
- {{3}} = Order Total

6. Submit for approval and wait for approval (usually 24-48 hours)

### Step 2: Configure Template in Odoo
1. Go to **Discuss > Configuration > WhatsApp Templates**
2. Find or create your order confirmation template
3. Fill in the required fields:
   - **Name**: Must match the template name in WhatsApp (e.g., `order_confirmation`)
   - **WhatsApp Template ID**: The ID from Meta Business Manager
   - **Status**: Should be "Approved"
   - **Model**: Sale Order
   - **Body**: Copy the template body from Meta
4. **Enable Auto Send**: Check the "Auto Send on Website Order" checkbox
5. Save the template

### Step 3: Configure Variables (Dynamic Content)
In the template form, you can configure variable fields to dynamically populate:
- Variable 1: `partner_id.name` (Customer name)
- Variable 2: `name` (Order number)
- Variable 3: `amount_total` (Order total)

### Step 4: Ensure Customer Phone Numbers
Make sure your customers have phone numbers in their contact records:
1. The system will use the **Mobile** field first
2. If Mobile is empty, it will use the **Phone** field
3. Without a phone number, no message will be sent

## How It Works

### Trigger Points
The module sends WhatsApp messages at these points:

1. **Order Confirmation**: When order is confirmed (state changes to 'sale')
2. **Payment Completion**: When payment transaction is successful
3. **Manual Send**: Users can still manually send WhatsApp messages from the order form

### Workflow
```
Customer Places Order
         ↓
Payment Completed
         ↓
Order Confirmed
         ↓
System Checks:
  - Is this a website order?
  - Is there an auto-send template?
  - Does customer have a phone number?
  - Has message been sent already?
         ↓
Send WhatsApp Message
         ↓
Mark as Sent
```

## Usage

### For Administrators

1. **Create Multiple Templates**: You can create different templates for different purposes
2. **Enable/Disable Auto-Send**: Toggle the "Auto Send on Website Order" field
3. **Only ONE Template**: Only one template should have auto-send enabled at a time

### For Sales Team

1. **Manual Send**: Click the WhatsApp button in the sale order form to send manually
2. **Check Status**: The system tracks if a message has been sent (field: whatsapp_msg_sent)
3. **Resend**: You can manually send messages even if auto-send failed

## Troubleshooting

### Message Not Sending

**Check 1: Template Configuration**
- Go to WhatsApp Templates
- Verify template has "Auto Send on Website Order" checked
- Verify template status is "Approved"
- Verify template is linked to Sale Order model

**Check 2: Customer Phone Number**
- Open the customer's contact record
- Check if Mobile or Phone field has a valid number
- Format should include country code (e.g., +1234567890)

**Check 3: WhatsApp Integration**
- Go to Settings > General Settings > Discuss
- Verify WhatsApp configuration is complete
- Test the connection

**Check 4: Logs**
Check Odoo logs for errors:
```bash
tail -f /var/log/odoo/odoo.log | grep -i whatsapp
```

### Template Variables Not Working

1. Verify variable fields are correctly mapped in the template
2. Check that the sale order has the required data
3. Variables use dot notation: `partner_id.name`, `name`, `amount_total`

### Multiple Messages Being Sent

- The system has safeguards to prevent duplicate sends
- The `whatsapp_msg_sent` field tracks if message was sent
- If you're getting duplicates, check for custom code that might be triggering multiple confirmations

## Customization

### Change When Messages Are Sent

Edit `/models/sale_order.py`:
```python
def action_confirm(self):
    """Override to send WhatsApp message on order confirmation"""
    res = super(SaleOrder, self).action_confirm()
    
    # Your custom logic here
    
    return res
```

### Add More Variables to Template

Edit the template variables in Odoo:
1. Go to WhatsApp Templates
2. Open your template
3. Add variable fields with field names from sale.order model

### Create Custom Template Content

In Meta Business Manager, create templates for:
- Order shipped notifications
- Delivery confirmations
- Invoice reminders
- Promotional messages

Then map them in Odoo with appropriate triggers.

## Security

- Only approved templates can be sent
- Customer phone numbers are validated
- Failed sends are logged but don't break the order process
- Messages are sent asynchronously to avoid blocking order confirmation

## Testing

### Test the Integration

1. **Create Test Order**:
   - Go to your website
   - Add a product to cart
   - Complete checkout with a test phone number
   - Confirm payment

2. **Check Results**:
   - Order should be created and confirmed
   - WhatsApp message should be sent
   - Check the sale order's `whatsapp_msg_sent` field (should be True)

3. **Verify in WhatsApp**:
   - Check the customer's WhatsApp for the message
   - Verify variables were populated correctly

## Support

For issues or questions:
1. Check Odoo logs for error messages
2. Verify WhatsApp template is approved in Meta Business Manager
3. Test with a known working phone number
4. Check that WhatsApp Business API is properly configured

## Technical Details

### Module Structure
```
whatsapp_website_integration/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── whatsapp_template.py
│   ├── sale_order.py
│   └── payment_transaction.py
├── views/
│   └── whatsapp_template_views.xml
└── data/
    └── whatsapp_template_data.xml
```

### Database Fields Added
- `whatsapp.template.auto_send_on_order` (Boolean)
- `sale.order.whatsapp_msg_sent` (Boolean)

### Dependencies
- `website_sale`: For website order functionality
- `whatsapp`: For WhatsApp integration

## Version History

### Version 1.0.0
- Initial release
- Auto-send WhatsApp messages on order confirmation
- Template configuration with auto-send toggle
- Integration with payment transactions
- Error handling and logging

## License
LGPL-3

## Author
Your Company - https://www.yourcompany.com
