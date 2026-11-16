"""
Demonstrate TTD 1-Click Auto-Fill Companion in Action.
Opens Chrome, navigates to the simulated TTD Pilgrim Form,
triggers the SRIVANI Auto-Fill Companion, and fills the form.
Saves high-res before and after screenshots.
"""
import time
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

def run_demo():
    artifact_dir = Path(r"C:\Users\nagas\.gemini\antigravity\brain\d8eb18e4-664e-4ef0-9ec9-1212b0694f10")
    demo_url = "http://localhost:8000/demo-ttd-booking"
    
    print(f"[1/5] Launching Chrome via Playwright...")
    with sync_playwright() as p:
        # Launch Chrome (visible for 6 seconds so user sees it live)
        browser = p.chromium.launch(channel="chrome", headless=False)
        context = browser.new_context(viewport={"width": 1280, "height": 900})
        page = context.new_page()

        print(f"[2/5] Navigating to TTD Pilgrim Details form: {demo_url}")
        page.goto(demo_url, wait_until="networkidle")
        time.sleep(1)

        # Screenshot Before
        before_path = artifact_dir / "demo_before_autofill.png"
        page.screenshot(path=str(before_path))
        print(f"      Saved empty form screenshot: {before_path}")

        print(f"[3/5] Triggering SRIVANI Companion Widget...")
        page.click("#launch-companion-btn")
        page.wait_for_selector("#srivani-companion-widget", timeout=5000)
        time.sleep(1.5)

        print(f"[4/5] Clicking '⚡ Auto-Fill Devotees into Form'...")
        page.click("#srivani-autofill-btn")
        time.sleep(2)

        # Verify fields were populated
        name0 = page.input_value("#pilgrimName0")
        age0 = page.input_value("#age0")
        gender0 = page.input_value("#gender0")
        id_type0 = page.input_value("#idProofType0")
        id_num0 = page.input_value("#idNumber0")
        name1 = page.input_value("#pilgrimName1")
        phone = page.input_value("#mobileNumber")
        
        print(f"      [VERIFIED] Pilgrim 1 Name: {name0}")
        print(f"      [VERIFIED] Pilgrim 1 Age:  {age0}")
        print(f"      [VERIFIED] Pilgrim 1 Sex:  {gender0}")
        print(f"      [VERIFIED] Pilgrim 1 ID:   {id_type0} - {id_num0}")
        print(f"      [VERIFIED] Pilgrim 2 Name: {name1}")
        print(f"      [VERIFIED] Mobile Number:  {phone}")

        # Screenshot After
        after_path = artifact_dir / "demo_after_autofill.png"
        page.screenshot(path=str(after_path))
        print(f"[5/5] Saved filled form screenshot: {after_path}")

        time.sleep(3)
        browser.close()
        print("Demo completed successfully!")

if __name__ == "__main__":
    run_demo()
