#!/usr/bin/env python3
import sys
import os
import time
from database import get_active_trials, get_all_trials, get_recent_logs, defuse_trial
from scanner import process_raw_email
from nag_engine import nag_engine, calculate_nag_parameters
from notifier import browser_alert_queue

def print_banner():
    print("""
======================================================
  🛡️  TRIAL SHIELD — SUBSCRIPTION WATCHDOG
  Nagging Engine Active • Protect Your Wallet
======================================================
""")

def list_active_watchlist():
    trials = get_active_trials()
    if not trials:
        print("✅ No active trials! Your wallet is completely safe.\n")
        return
    
    print(f"🚨 ACTIVE WATCHLIST ({len(trials)} trial{'s' if len(trials) > 1 else ''} being nagged):")
    print("-" * 65)
    for t in trials:
        interval, urgency, time_left = calculate_nag_parameters(t['trial_end_date'], t.get('nag_intensity', 'relentless'))
        urgency_emoji = "🔴" if urgency == "CRITICAL" else ("🟠" if urgency == "HIGH" else "🟡")
        print(f"{urgency_emoji} [ID #{t['id']}] {t['service_name'].upper()}")
        print(f"   ⏱️  Time Left: {time_left} (Ends: {t['trial_end_date']})")
        print(f"   💰 Fee at risk: {t['cost'] or 'Unknown subscription fee'}")
        print(f"   🔔 Nag Interval: Every {interval} minutes (Alerted {t['nag_count']} times so far)")
        if t['cancel_url']:
            print(f"   🔗 Direct Cancel Link: {t['cancel_url']}")
        print("-" * 65)
    print()

def simulate_trial_email():
    print("\n--- ⚡ SIMULATE INCOMING TRIAL ENDING EMAIL ---")
    print("Presets:")
    print("1. Adobe CC ($54.99/mo, trial ends today)")
    print("2. Netflix Premium ($22.99/mo, renews tomorrow)")
    print("3. Spotify Premium ($10.99/mo, 3 days left)")
    print("4. Custom input")
    choice = input("Select preset (1-4) [1]: ").strip() or "1"

    if choice == "1":
        sender = "Adobe Billing <billing@adobe.com>"
        subject = "Action Required: Your Adobe Creative Cloud trial is ending"
        body = "Hi Bhavik,\nYour 7-day free trial of Adobe Creative Cloud is ending today. You will be charged $54.99/mo starting tomorrow unless you cancel. To cancel, visit: https://account.adobe.com/plans/cancel"
    elif choice == "2":
        sender = "Netflix <info@mailer.netflix.com>"
        subject = "Upcoming charge notice for Netflix"
        body = "Hello,\nYour subscription will automatically renew on tomorrow. You will be billed $22.99 for your Ultra HD plan. Cancel at: https://netflix.com/youraccount"
    elif choice == "3":
        sender = "Spotify <no-reply@spotify.com>"
        subject = "3 days left in your Spotify Premium free trial"
        body = "Hey,\nYou have 3 days left in your trial. After that, your card will be billed $10.99/month. Cancel at: https://spotify.com/account/cancel"
    else:
        sender = input("Sender header (e.g. Service <info@service.com>): ")
        subject = input("Subject: ")
        body = input("Body text: ")

    result = process_raw_email(sender, subject, body)
    if result['status'] == 'TRIAL_DETECTED':
        print(f"\n🎯 SUCCESS! Detected active trial for '{result['data']['service_name']}'!")
        print(f"   Expiry: {result['data']['trial_end_date']}")
        print(f"   Cost: {result['data']['cost']}")
        print("   Watchdog started nagging! Check active trials list.\n")
    else:
        print(f"\n⚠️ Processed with status: {result['status']}")

def simulate_cancellation_email():
    print("\n--- 🛡️ SIMULATE CANCELLATION CONFIRMATION (DEFUSAL) ---")
    service = input("Enter service name to defuse (e.g. Adobe, Netflix, Spotify): ").strip() or "Adobe"
    sender = f"{service} Support <support@{service.lower()}.com>"
    subject = f"Confirmation of cancellation for your {service} subscription"
    body = f"Hello,\nWe're sorry to see you go! This email confirms that your {service} subscription has been canceled. You will not be charged."

    result = process_raw_email(sender, subject, body)
    if result['status'] == 'TRIAL_DEFUSED':
        print(f"\n🎉 SHIELD DEFUSED! Cancellation confirmed for {service}!")
        print("   The watchdog has stopped nagging. Your money is saved!\n")
    else:
        print(f"\n⚠️ Result: {result['status']}")

def test_alert():
    print("\nTesting macOS Desktop Notification...")
    send_macos_notification("🛡️ Trial Shield Alert Test", "Nagging watchdog standing by on your Mac!", sound="Basso")
    send_voice_alert("Trial Shield alert test successful.")
    print("Done! You should see a notification on your desktop and hear an audio alert.\n")

def main_menu():
    print_banner()
    while True:
        print("Menu:")
        print("1. 📋 View Active Watchlist & Status")
        print("2. ⚡ Simulate Incoming Trial Ending Email (Start Nagging)")
        print("3. 🛡️ Simulate Cancellation Confirmation Email (Defuse & Stop)")
        print("4. 🔔 Test Mac Notification & Voice Alert")
        print("5. 📜 View Recent Nag Logs")
        print("6. 🌐 Start Web Dashboard (http://localhost:5055)")
        print("0. Exit")
        
        choice = input("\nEnter choice [1-6]: ").strip()
        if choice == "1":
            list_active_watchlist()
        elif choice == "2":
            simulate_trial_email()
        elif choice == "3":
            simulate_cancellation_email()
        elif choice == "4":
            test_alert()
        elif choice == "5":
            logs = get_recent_logs(15)
            print("\nRecent Nag Dispatches:")
            for l in logs:
                print(f"[{l['created_at']}] [{l['channel']}] {l['service_name']} ({l['urgency']}): {l['message']}")
            print()
        elif choice == "6":
            print("\nStarting Web Dashboard at http://localhost:5055 ...")
            os.system(f"{sys.executable} server.py")
        elif choice == "0":
            print("Exiting Trial Shield. Stay vigilant!")
            break
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main_menu()
