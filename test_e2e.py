import httpx
import asyncio

async def test_flow():
    base_url = "http://127.0.0.1:8000"
    
    async with httpx.AsyncClient() as client:
        # --- 1. Provider Flow ---
        print("\n--- Testing Provider Role ---")
        login_data = {"username": "provider1@test.com", "password": "pass123"}
        r = await client.post(f"{base_url}/api/auth/login", data=login_data, follow_redirects=False)
        assert r.status_code == 303
        print(f"✅ Login POST successful. Redirecting to: {r.headers.get('location')}")
        
        # Load Dashboard
        r = await client.get(f"{base_url}/provider/dashboard", follow_redirects=True)
        assert r.status_code == 200
        assert "Provider Dashboard" in r.text
        assert "Sharma" in r.text
        print("✅ Dashboard loaded successfully.")
        
        # Load Menu
        r = await client.get(f"{base_url}/provider/menu", follow_redirects=True)
        assert r.status_code == 200
        assert "My Menu" in r.text
        assert "Dal Rice" in r.text
        print("✅ Menu loaded successfully.")
        
        # --- 2. Customer Flow ---
        print("\n--- Testing Customer Role ---")
        client.cookies.clear()
        login_data = {"username": "rahul@test.com", "password": "pass123"}
        r = await client.post(f"{base_url}/api/auth/login", data=login_data, follow_redirects=False)
        assert r.status_code == 303
        
        # Load Home
        r = await client.get(f"{base_url}/customer/home", follow_redirects=True)
        assert r.status_code == 200
        assert "Explore" in r.text or "Discover" in r.text
        assert "Rahul" in r.text
        print("✅ Home loaded successfully.")
        
        # Load Cart
        r = await client.get(f"{base_url}/customer/cart", follow_redirects=True)
        assert r.status_code == 200
        assert "Your Cart" in r.text
        print("✅ Cart loaded successfully.")
        
        # --- 3. Delivery Flow ---
        print("\n--- Testing Delivery Role ---")
        client.cookies.clear()
        login_data = {"username": "delivery1@test.com", "password": "pass123"}
        r = await client.post(f"{base_url}/api/auth/login", data=login_data, follow_redirects=False)
        assert r.status_code == 303, f"Delivery login failed: {r.status_code}"
        print(f"  Login redirect: {r.headers.get('location')}")
        
        # Load Dashboard
        r = await client.get(f"{base_url}/delivery/dashboard", follow_redirects=True)
        if r.status_code != 200:
            print(f"  FAILED status={r.status_code}, url={r.url}")
            print(f"  Response (first 500 chars): {r.text[:500]}")
        assert r.status_code == 200, f"Delivery dashboard status={r.status_code}"
        print("✅ Delivery dashboard loaded successfully.")
        
        # --- 4. Admin Flow ---
        print("\n--- Testing Admin Role ---")
        client.cookies.clear()
        login_data = {"username": "admin@digibhoj.com", "password": "pass123"}
        r = await client.post(f"{base_url}/api/auth/login", data=login_data, follow_redirects=False)
        assert r.status_code == 303, f"Admin login failed: {r.status_code}"
        print(f"  Login redirect: {r.headers.get('location')}")
        
        # Load Dashboard
        r = await client.get(f"{base_url}/admin/dashboard", follow_redirects=True)
        if r.status_code != 200:
            print(f"  FAILED status={r.status_code}, url={r.url}")
            print(f"  Response (first 500 chars): {r.text[:500]}")
        assert r.status_code == 200, f"Admin dashboard status={r.status_code}"
        print("✅ Admin dashboard loaded successfully.")
        
        print("\n🎉 All core SSR Authentication and Routing flows verified successfully!")
        
        print("\nAll SSR Authentication Flows Verified Successfully! 🎉")

if __name__ == "__main__":
    asyncio.run(test_flow())
