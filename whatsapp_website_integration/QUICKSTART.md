# Quick Start Guide - WhatsApp Order Confirmation

## 🚀 Quick Setup (5 Minutes)

### Step 1: Install the Module (2 minutes)
1. Copy `whatsapp_website_integration` folder to your Odoo addons directory
2. Restart Odoo service
3. Go to **Apps** → Update Apps List
4. Search "WhatsApp Website Order" → Install

### Step 2: Create WhatsApp Template in Meta (30 minutes - includes approval wait time)
1. Go to https://business.facebook.com/
2. **WhatsApp Manager** → **Message Templates** → **Create Template**
3. Fill in:
   - **Name**: `order_confirmation` (must be lowercase, no spaces)
   - **Category**: **Transactional**
   - **Language**: Your preferred language
   
4. **Template Body**:
```
Hello {{1}},

Thank you for your order {{2}}!

Your order has been confirmed and is being processed.

Order Total: {{3}}

We will notify you once your order is ready for delivery.

Thank you for shopping with us!
```

5. Click **Submit** and wait for approval (usually takes a few hours)

### Step 3: Configure in Odoo (2 minutes)
1. Go to **Discuss** → **Configuration** → **WhatsApp Templates**
2. Click **Create** or edit existing template
3. Fill in:
   - **Name**: `order_confirmation` (must match Meta template name exactly)
   - **WhatsApp Template ID**: Copy from Meta Business Manager
   - **Status**: Select "Approved" (after Meta approves it)
   - **Model**: Sale Order
   - **Body**: Same as Meta template body
   - **☑️ Auto Send on Website Order**: **CHECK THIS BOX** ✓

4. Configure **Variables** (click Edit on variables):
   - **Variable 1**: `{{partner_id.name}}` → Customer Name
   - **Variable 2**: `{{name}}` → Order Number  
   - **Variable 3**: `{{amount_total}}` → Order Total

5. **Save**

### Step 4: Test (1 minute)
1. Go to your website
2. Add product to cart
3. Complete checkout with your phone number (include country code: +1234567890)
4. Complete payment
5. Check your WhatsApp! 📱

## ✅ Verification Checklist

- [ ] Module installed and no errors in log
- [ ] WhatsApp template created in Meta Business Manager
- [ ] Template approved by Meta (Status: Approved)
- [ ] Template configured in Odoo with same name
- [ ] "Auto Send on Website Order" checkbox is checked ✓
- [ ] Variables are mapped correctly
- [ ] Test customer has phone number in Mobile or Phone field
- [ ] WhatsApp Business API is configured in Odoo settings

## 🔧 Common Issues

### "No template configured for auto-send"
→ Make sure template has "Auto Send on Website Order" checked

### "Customer has no phone number"
→ Add phone number to customer contact (Mobile or Phone field)
→ Include country code: +1234567890

### "Template not found"
→ Template name in Odoo must EXACTLY match name in Meta (case-sensitive)

### "Template not approved"
→ Wait for Meta to approve (check Meta Business Manager)
→ Change Status to "Approved" in Odoo after Meta approves

### Variables showing as {{1}}, {{2}}
→ Map variables in template: Edit → Variables section
→ Use field names: partner_id.name, name, amount_total

## 📝 Example Template Names

Good ✅:
- `order_confirmation`
- `order_received`
- `payment_confirmed`

Bad ❌:
- `Order Confirmation` (has spaces and capitals)
- `order-confirmation` (has dash)
- `OrderConfirmation` (has capitals)

## 🎯 Pro Tips

1. **Only ONE template** should have "Auto Send" checked at a time
2. **Always include country code** in phone numbers (+1, +44, +91, etc.)
3. **Test first** with your own phone number
4. **Check logs** if something doesn't work: Settings → Technical → Logging
5. **Variables are case-sensitive**: use `name` not `Name`

## 📞 Support

If you're still having issues:
1. Check Odoo logs: `tail -f /var/log/odoo/odoo.log | grep -i whatsapp`
2. Verify WhatsApp Business API connection in Settings
3. Test sending manual WhatsApp from a sale order
4. Make sure template Status is "Approved" in both Meta and Odoo

## 🎉 You're Done!

Customers will now automatically receive WhatsApp confirmations when they order from your website!
