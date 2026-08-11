#!/usr/bin/env python3
"""
Debug script to check QR code generation status in Odoo.
This can be run from the Odoo shell to diagnose QR code printing issues.

Usage in Odoo shell:
    cd /path/to/odoo
    python odoo-bin shell -d database_name
    >>> exec(open('path/to/debug_qr_code.py').read())
"""

import logging
from odoo import env

_logger = logging.getLogger(__name__)

def check_qr_code_generation():
    """Check QR code generation for all custom inventory products"""
    try:
        # Set logging to see debug messages
        logging.basicConfig(level=logging.DEBUG)

        print("\n" + "="*80)
        print("QR CODE GENERATION DEBUG CHECK")
        print("="*80 + "\n")

        # Get all custom inventory products
        products = env['custom.inventory.product'].search([])

        if not products:
            print("No products found in custom.inventory.product")
            return

        print(f"Found {len(products)} products\n")

        # Check each product
        failed_count = 0
        success_count = 0

        for idx, product in enumerate(products, 1):
            print(f"\n[{idx}/{len(products)}] Checking Product: {product.name}")
            print("-" * 60)

            try:
                # Try to regenerate QR code
                print(f"  ID: {product.id}")
                print(f"  Category: {product.category_id.name if product.category_id else 'N/A'}")
                print(f"  Reference: {product.default_code or 'N/A'}")
                print(f"  Has QR Code: {bool(product.qr_code)}")
                print(f"  QR Code Size: {len(product.qr_code) if product.qr_code else 0} bytes")
                print(f"  QR URL: {product.qr_url or 'N/A'}")

                # Attempt to regenerate
                print(f"\n  Regenerating QR code...")
                try:
                    product.generate_qr()
                    print(f"  ✓ QR code regenerated successfully")
                    print(f"    New size: {len(product.qr_code) if product.qr_code else 0} bytes")
                    success_count += 1
                except Exception as e:
                    print(f"  ✗ ERROR regenerating: {str(e)}")
                    failed_count += 1

            except Exception as e:
                print(f"  ✗ ERROR checking product: {str(e)}")
                failed_count += 1

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)
        print(f"Total Products: {len(products)}")
        print(f"Successfully Generated: {success_count}")
        print(f"Failed: {failed_count}")
        print("="*80 + "\n")

        return {
            'total': len(products),
            'success': success_count,
            'failed': failed_count,
        }

    except Exception as e:
        print(f"\nCRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def test_pdf_report():
    """Test PDF report generation"""
    try:
        print("\n" + "="*80)
        print("PDF REPORT GENERATION TEST")
        print("="*80 + "\n")

        # Get the report
        report = env['ir.actions.report'].search([
            ('report_name', '=', 'IH_30north_Inventory_assets.report_qr_code_template')
        ], limit=1)

        if not report:
            print("Report not found: IH_30north_Inventory_assets.report_qr_code_template")
            return False

        print(f"Found Report: {report.name}")
        print(f"Report Type: {report.report_type}")
        print(f"Model: {report.model}")

        # Get a sample product with QR code
        product = env['custom.inventory.product'].search([('qr_code', '!=', False)], limit=1)

        if not product:
            print("\nNo products with QR code found. Generating one...")
            product = env['custom.inventory.product'].search([], limit=1)
            if product:
                product.generate_qr()
                print(f"Generated QR code for: {product.name}")
            else:
                print("No products found at all!")
                return False

        print(f"\nTesting with Product: {product.name}")
        print(f"Has QR Code: {bool(product.qr_code)}")
        print(f"QR URL: {product.qr_url}")

        # Try to generate PDF
        print("\nGenerating PDF...")
        try:
            pdf_content, content_type = env['ir.actions.report']._render_qweb_pdf(
                'IH_30north_Inventory_assets.report_qr_code_template',
                [product.id]
            )

            if pdf_content:
                print(f"✓ PDF generated successfully")
                print(f"  Size: {len(pdf_content)} bytes")
                print(f"  Type: {content_type}")
                return True
            else:
                print(f"✗ PDF generation returned empty content")
                return False

        except Exception as e:
            print(f"✗ ERROR generating PDF: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    except Exception as e:
        print(f"\nCRITICAL ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


# Run checks
if __name__ == '__main__':
    print("Starting QR Code Debug Checks...")
    check_qr_code_generation()
    test_pdf_report()

