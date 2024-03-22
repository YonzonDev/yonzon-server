from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv, find_dotenv

import pandas as pd
import requests
import zipfile
import json
import time

import io
import os


_ = load_dotenv(find_dotenv())

app = FastAPI(title="Yonzon Back End", version="0.0.1", docs_url="/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


with open("users.json", "r") as data:
    users = json.load(data)

sheety_endpoint = os.environ.get(f"SHEETY_ENDPOINT")
bearer_token = os.environ.get(f"BEARER_TOKEN")

headers = {"Authorization": f"Bearer {bearer_token}"}


@app.post("/signin", tags=["Auth"])
async def sign_in(username: str = Form(...), password: str = Form(...)):
    print("Tag: Auth\nEndpoint: `/sign-in`")
    for key, value in users.items():
        if username in value["username"] and password == value["password"]:
            return {
                "access_token": username,
                "access_type": value["access_type"],
                "token_type": "bearer",
                "response": f"Sign in for {username} was successful",
            }
    raise HTTPException(
        status_code=401,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.post("/change-password", tags=["Auth"])
async def change_password(
    username: str = Form(...), password: str = Form(...), new_password: str = Form(...)
):
    print("Tag: Auth\nEndpoint: `/change-password`")
    for key, value in users.items():
        if username == key and password == value["password"]:
            value["password"] = new_password

            with open("users.json", "w") as data:
                json.dump(users, data, indent=4)
            return {
                "access_token": username,
                "access_type": value["access_type"],
                "token_type": "bearer",
                "response": f"Change password for {username} was successful",
            }
    raise HTTPException(
        status_code=401,
        detail="Incorrect password",
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.get("/get-items", tags=["Inventory"])
async def get_items():
    print("Tag: Inventory\nEndpoint: `/get-items`")
    response = requests.get(url=f"{sheety_endpoint}/inventory", headers=headers).json()
    if not response["inventory"]:
        raise HTTPException(status_code=404, detail="Items do not exist")

    return {
        "response": "Data was fetched successfully",
        "total": len(response["inventory"]),
        "data": response["inventory"],
    }


@app.get("/get-item/{item_id}", tags=["Inventory"])
async def get_item(item_id: int):
    try:
        print("Tag: Inventory\nEndpoint: `/get-item`")
        response = requests.get(
            url=f"{sheety_endpoint}/inventory", headers=headers
        ).json()

        is_exists = False
        for row in response["inventory"]:
            if row["id"] == item_id:
                is_exists = True

        if not is_exists:
            raise HTTPException(status_code=404, detail="Item not found")

        response = requests.get(
            url=f"{sheety_endpoint}/inventory/{item_id}", headers=headers
        ).json()
        return {
            "response": "Data was fetched successfully",
            "data": response["inventory"],
        }
    except:
        raise HTTPException(status_code=500, detail="Google Sheets API issues")


@app.post("/add-item", tags=["Inventory"])
async def add_item(
    model: str = Form(...),
    product: str = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
):
    try:
        print("Tag: Inventory\nEndpoint: `/add-item`")
        response = requests.get(
            url=f"{sheety_endpoint}/inventory", headers=headers
        ).json()

        is_exists = False
        for row in response["inventory"]:
            if row["model"].lower() == model.lower():
                is_exists = True

        if is_exists:
            raise HTTPException(status_code=404, detail=f"Item already exists")

        item_data = {
            "inventory": {
                "model": model,
                "product": product,
                "price": price,
                "quantity": quantity,
                "total": quantity * price,
            }
        }
        response = requests.post(
            url=f"{sheety_endpoint}/inventory", json=item_data, headers=headers
        )
        return {
            "response": "Data was added successfully",
        }
    except:
        raise HTTPException(status_code=500, detail="Google Sheets API issues")


@app.put("/update-item", tags=["Inventory"])
async def update_item(
    item_id: int = Form(...),
    price: float = Form(...),
    quantity: int = Form(...),
):
    try:
        print("Tag: Inventory\nEndpoint: `/update-item`")

        # Retrieve inventory data
        response = requests.get(
            url=f"{sheety_endpoint}/inventory", headers=headers
        ).json()

        # Check if item exists
        is_exists = False
        for row in response["inventory"]:
            if row["id"] == item_id:
                is_exists = True
                # existing_quantity = row["quantity"]
                break

        if not is_exists:
            raise HTTPException(status_code=404, detail="Item not found")

        # Prepare data for update
        item_data = {
            "price": price,
            "quantity": quantity,
            # + existing_quantity,  # Adding old quantity with new quantity
            "total": quantity * price,  # Recalculating total based on updated quantity
        }

        # Update item
        response = requests.put(
            url=f"{sheety_endpoint}/inventory/{item_id}",
            json={"inventory": item_data},
            headers=headers,
        )

        return {
            "response": "Data was updated successfully",
        }
    except:
        raise HTTPException(status_code=500, detail="Google Sheets API issues")


@app.delete("/delete-item/{item_id}", tags=["Inventory"])
async def delete_item(item_id: int):
    try:
        print("Tag: Inventory\nEndpoint: `/delete-item`")
        response = requests.get(
            url=f"{sheety_endpoint}/inventory", headers=headers
        ).json()

        is_exists = False
        for row in response["inventory"]:
            if row["id"] == item_id:
                is_exists = True

        if not is_exists:
            raise HTTPException(status_code=404, detail="Item not found")

        response = requests.delete(
            url=f"{sheety_endpoint}/inventory/{item_id}", headers=headers
        )
        return {
            "response": "Data was deleted successfully",
        }
    except:
        raise HTTPException(status_code=500, detail="Google Sheets API issues")


@app.get("/get-transactions", tags=["Sales"])
async def get_transactions():
    try:
        print("Tag: Sales\nEndpoint: `/get-transactions`")
        response = requests.get(url=f"{sheety_endpoint}/sales", headers=headers).json()
        if not response["sales"]:
            raise HTTPException(status_code=404, detail="Sales do not exist")

        return {
            "response": "Data was fetched successfully",
            "total": len(response["sales"]),
            "data": response["sales"],
        }
    except:
        raise HTTPException(status_code=500, detail="Google Sheets API issues")


@app.post("/add-transaction", tags=["Sales"])
async def add_transaction(
    item_id: int = Form(...),
    model: str = Form(...),
    product: str = Form(...),
    orders: int = Form(...),
    price: int = Form(...),
    date: str = Form(...),
):
    try:
        print("Tag: Sales\nEndpoint: `/add-transaction`")
        # Get the product by ID
        inventory_response = requests.get(
            url=f"{sheety_endpoint}/inventory", headers=headers
        ).json()

        is_exists = False
        for item in inventory_response["inventory"]:
            if item["id"] == item_id:
                is_exists = True

        if not is_exists:
            raise HTTPException(status_code=404, detail="Sales does not exist")

        item_data = {
            "sale": {
                "product_id": item_id,
                "model": model,
                "product": product,
                "orders": orders,
                "price": price,
                "date": date,
            }
        }
        # Post on sales sheet
        requests.post(url=f"{sheety_endpoint}/sales", json=item_data, headers=headers)
        time.sleep(1)

        # Put on inventory sheet
        for item in inventory_response["inventory"]:
            if item["id"] == item_id:
                if item["quantity"] >= 0:
                    item_data = {
                        "inventory": {
                            "quantity": item["quantity"] - orders,
                        }
                    }
                    print(f"{item['quantity']} - {orders}")
                    update_quantity = requests.put(
                        url=f"{sheety_endpoint}/inventory/{item_id}",
                        json=item_data,
                        headers=headers,
                    )

                    return {"data": "Data was added successfully"}
        raise HTTPException(
            status_code=404, detail=f"Insufficient quantity for {orders} order/s"
        )
    except:
        raise HTTPException(status_code=500, detail="Google Sheets API issues")


@app.get("/get-csv", tags=["Utilities"])
async def get_csv():
    try:
        print("Tag: Utilities\nEndpoint: `/get-csv`")
        # Get all inventory sheet rows
        inventory_response = requests.get(
            f"{sheety_endpoint}/inventory", headers=headers
        ).json()

        if not inventory_response["inventory"]:
            raise HTTPException(status_code=404, detail="Inventory items do not exist")

        inventory_df = pd.DataFrame.from_dict(inventory_response["inventory"])

        # Get all sales sheet rows
        sales_response = requests.get(
            f"{sheety_endpoint}/sales", headers=headers
        ).json()

        if not sales_response["sales"]:
            raise HTTPException(status_code=404, detail="Sales data does not exist")

        sales_df = pd.DataFrame.from_dict(sales_response["sales"])

        # Create a BytesIO object to hold the zip file in memory
        zip_buffer = io.BytesIO()

        # Create a zip file in the BytesIO object
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            # Add inventory.csv to the zip file
            with zipf.open("inventory.csv", "w") as inventory_file:
                inventory_df.to_csv(inventory_file, index=False)

            # Add sales.csv to the zip file
            with zipf.open("sales.csv", "w") as sales_file:
                sales_df.to_csv(sales_file, index=False)

        # Set the BytesIO object's cursor to the beginning
        zip_buffer.seek(0)

        # Return the zip file as a response
        return StreamingResponse(
            iter([zip_buffer.getvalue()]),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=data.zip"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail="Google Sheets API issues")
