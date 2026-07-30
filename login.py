"""
login.py
--------
One-time setup script: Meesho pe login karke session cookies save karne ke liye.
"""

import os
import undetected_chromedriver as uc

def setup_persistent_session():
    # Exact wahi folder path jo scraper.py mein use kiya hai
    profile_path = os.path.abspath(os.path.join(os.getcwd(), "chrome_profile"))
    
    options = uc.ChromeOptions()
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-data-dir={profile_path}")
    options.add_argument("--disable-blink-features=AutomationControlled")

    print("Browser launch ho raha hai...")
    # Make sure version_main match kare tumhare system Chrome se (jaise pehle 150 fix kiya tha)
    driver = uc.Chrome(options=options, version_main=150)
    
    try:
        # Meesho homepage open karo
        driver.get("https://www.meesho.com/")
        
        print("\n" + "="*60)
        print(" ACTION REQUIRED: Browser open ho gaya hai.")
        print(" 1. Profile section mein jao aur Phone Number daalo.")
        print(" 2. OTP verify karke completely login kar lo.")
        print(" 3. Jab login puri tarah successful ho jaye...")
        print("="*60 + "\n")
        
        # Terminal yahan pause ho jayega
        input("👉 LOGIN COMPLETE HONE KE BAAD YAHAN ENTER DABAO... ")
        
    finally:
        # Enter dabate hi browser close hoga aur data disk pe save ho jayega
        driver.quit()
        print("✅ Session cookies and local storage saved successfully!")
        print("Ab tum app.py run karke bulk pincode checker use kar sakte ho.")

if __name__ == "__main__":
    setup_persistent_session()