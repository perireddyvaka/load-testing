#!/usr/bin/env python3
import requests
import random
import string
from time import sleep

# ================= CONFIG =================
API_BASE_URL = "http://10.2.16.116:8610"  # <-- CHANGE if your backend is on another host/port
USER_REQUEST_ENDPOINT = "/onboard/user-request"  # e.g. "/users/user-request" if router has prefix
APPROVE_VENDOR_ENDPOINT = "/onboard/approve-vendor"  # e.g. "/users/approve-vendor" if router has prefix

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE3NjU1Mjk0OTgsInN1YiI6IjEifQ.HVfX0I8SrEph4oorWeDxOitbYcT76EmxQy3Jqmk_FaM"  # e.g. the one you used for /import

TOTAL_USERS = 500
USER_TYPE = "VENDOR"  # as expected by your create_vendor API
EMAIL_DOMAIN = "ctop.in"  # any domain you like; must not be temp/disposable
# ==========================================


def random_phone():
    # simple 10-digit mobile-like number
    start = random.randint(6000000000, 9999999999)
    return str(start)


def random_suffix(length=4):
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def create_user_requests():
    """Send 500 /user-request calls and return list of created emails"""
    created_emails = []

    for i in range(1, TOTAL_USERS + 1):
        username = f"vendor_{i:03d}_{random_suffix(3)}"
        email = f"{username}@{EMAIL_DOMAIN}"

        payload = {
            "username": username,
            "firstname": "Auto",
            "lastname": f"Vendor{i:03d}",
            "email": email,
            "location": "Hyderabad",
            "organisation": "Auto Test Org",
            "designation": "Vendor",
            "contact": random_phone(),
            "vendor_website": f"https://{username}.example.com",
            # vendor_email not needed for user_type=vendor
            "vendor_email": "",
            "user_type": USER_TYPE,  # "VENDOR"
        }

        try:
            resp = requests.post(
                API_BASE_URL + USER_REQUEST_ENDPOINT,
                data=payload,  # form-data (application/x-www-form-urlencoded)
                timeout=10,
            )
        except Exception as e:
            print(f"[REQUEST {i}] EXCEPTION: {e}")
            continue

        if resp.status_code == 200:
            data = resp.json()
            print(f"[REQUEST {i}] OK: {data.get('email')} status={data.get('status')}")
            created_emails.append(email)
        else:
            print(
                f"[REQUEST {i}] FAILED ({resp.status_code}): {resp.text}"
            )

        # small delay to avoid hammering
        sleep(0.05)

    return created_emails


def approve_users(emails):
    """Approve each email via /approve-vendor"""
    headers = {
        "Authorization": f"Bearer {TOKEN}",
    }

    for idx, email in enumerate(emails, start=1):
        try:
            # email is a query parameter in your approve_vendor function
            resp = requests.post(
                API_BASE_URL + APPROVE_VENDOR_ENDPOINT,
                params={"email": email},
                headers=headers,
                timeout=10,
            )
        except Exception as e:
            print(f"[APPROVE {idx}] {email} EXCEPTION: {e}")
            continue

        if resp.status_code == 200:
            data = resp.json()
            print(f"[APPROVE {idx}] OK: {email} -> user_id={data.get('user_id')}")
        else:
            print(
                f"[APPROVE {idx}] FAILED for {email} "
                f"({resp.status_code}): {resp.text}"
            )

        sleep(0.05)


def main():
    print(f"=== Creating {TOTAL_USERS} vendor user requests ===")
    emails = create_user_requests()
    print(f"\n=== Done user-request. Created {len(emails)} requests. ===")

    if not emails:
        print("No requests created, aborting approvals.")
        return

    print("\n=== Approving created vendors ===")
    approve_users(emails)
    print("\n=== Finished ===")


if __name__ == "__main__":
    main()
