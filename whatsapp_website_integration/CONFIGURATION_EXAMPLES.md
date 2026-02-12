# Configuration Examples

## Example 1: Basic Order Confirmation Template

### Meta Business Manager Template
```
Template Name: order_confirmation
Category: Transactional
Language: English

Body:
Hello {{1}},

Thank you for your order {{2}}!

Your order has been confirmed and is being processed.

Order Total: {{3}}

We will notify you once your order is ready for delivery.

Thank you for shopping with us!
```

### Odoo Configuration
```
Name: order_confirmation
Model: sale.order
Status: approved
Auto Send on Website Order: ✓ (checked)

Variables:
  {{1}}: partner_id.name
  {{2}}: name
  {{3}}: amount_total
```

---

## Example 2: Order with Delivery Date

### Meta Business Manager Template
```
Template Name: order_with_delivery
Category: Transactional
Language: English

Body:
Hi {{1}}! 👋

Your order {{2}} is confirmed!

📦 Order Details:
• Total: {{3}}
• Expected Delivery: {{4}}

Track your order at: {{5}}

Questions? Reply to this message!
```

### Odoo Configuration
```
Name: order_with_delivery
Model: sale.order
Status: approved
Auto Send on Website Order: ✓ (checked)

Variables:
  {{1}}: partner_id.name
  {{2}}: name
  {{3}}: amount_total
  {{4}}: commitment_date
  {{5}}: website_id.domain
```

---

## Example 3: Multilingual Template (Arabic)

### Meta Business Manager Template
```
Template Name: order_confirmation_ar
Category: Transactional
Language: Arabic

Body:
مرحباً {{1}}،

شكراً لطلبك رقم {{2}}!

تم تأكيد طلبك وجاري المعالجة.

إجمالي الطلب: {{3}}

سنقوم بإعلامك عندما يكون طلبك جاهزاً للتسليم.

شكراً لتسوقك معنا!
```

### Odoo Configuration
```
Name: order_confirmation_ar
Model: sale.order
Status: approved
Auto Send on Website Order: ✓ (checked)

Variables:
  {{1}}: partner_id.name
  {{2}}: name
  {{3}}: amount_total
```

---

## Available Fields for Variables

### Customer Information
- `partner_id.name` - Customer name
- `partner_id.email` - Customer email
- `partner_id.phone` - Customer phone
- `partner_id.mobile` - Customer mobile
- `partner_id.street` - Street address
- `partner_id.city` - City
- `partner_id.country_id.name` - Country

### Order Information
- `name` - Order number (e.g., SO001)
- `amount_total` - Total amount
- `amount_untaxed` - Amount before tax
- `amount_tax` - Tax amount
- `date_order` - Order date
- `commitment_date` - Delivery date
- `state` - Order status

### Company Information
- `company_id.name` - Company name
- `company_id.phone` - Company phone
- `company_id.email` - Company email
- `company_id.website` - Company website

### Website Information
- `website_id.name` - Website name
- `website_id.domain` - Website domain

### User/Salesperson Information
- `user_id.name` - Salesperson name
- `user_id.phone` - Salesperson phone
- `user_id.email` - Salesperson email

---

## How to Use Custom Fields

If you have custom fields in your sale order model:

1. Find the technical name of the field
2. Use it in the variable mapping
3. Example: If you added `x_studio_delivery_notes` field
   ```
   {{4}}: x_studio_delivery_notes
   ```

---

## Tips for Writing Good Templates

### ✅ Do's
- Keep it short and clear
- Use customer's name for personalization
- Include order number for reference
- Add a clear call-to-action
- Use emojis sparingly (1-2 max)
- Test with real data before going live

### ❌ Don'ts
- Don't make it too long (WhatsApp has limits)
- Don't use ALL CAPS
- Don't add too many variables (3-5 is optimal)
- Don't forget to get template approved first
- Don't use special characters in template name

---

## Testing Your Template

### Test Scenario 1: New Customer Order
```python
Customer: John Doe
Order: SO001
Total: $150.50
Phone: +1234567890

Expected WhatsApp:
"Hello John Doe,

Thank you for your order SO001!

Your order has been confirmed and is being processed.

Order Total: $150.50

We will notify you once your order is ready for delivery.

Thank you for shopping with us!"
```

### Test Scenario 2: Existing Customer
```python
Customer: Jane Smith
Order: SO002
Total: €75.00
Phone: +44123456789

Expected WhatsApp:
(Same format with Jane's details)
```

---

## Troubleshooting Variable Issues

### Problem: Variable shows as {{1}}
**Solution**: Variable not mapped correctly
```
Wrong: {{partner_id.name}}
Right: partner_id.name (no brackets in Odoo)
```

### Problem: Empty variable value
**Solution**: Field is empty in order
- Check the sale order has the data
- Use a different field or add default value

### Problem: Date formatting issues
**Solution**: Format dates in Odoo
```
Instead of: commitment_date
Use: commitment_date.strftime('%Y-%m-%d')
```

This requires custom code in the model.
