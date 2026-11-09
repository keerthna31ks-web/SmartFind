from email.mime import image

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, Field
from typing import Literal
from database import get_connection
from difflib import SequenceMatcher
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

CAMPUS_LOCATIONS = [
    "Library",
    "Classroom",
    "Laboratory",
    "Canteen",
    "Auditorium",
    "Parking Area",
    "Reception",
    "Sports Ground",
    "Bus Stop",
    "Security Office",
    "Other"
]

model = SentenceTransformer("all-MiniLM-L6-v2")
import os
import shutil
import uuid


app = FastAPI(title="smartfind")
app.mount("/static", StaticFiles(directory="static"), name="static")

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

def save_image(image: UploadFile):
    extension = os.path.splitext(image.filename)[1].lower()

    allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only JPG, JPEG, PNG and WEBP images are allowed"
        )

    filename = f"{uuid.uuid4()}{extension}"

    file_path = os.path.join(UPLOAD_DIR, filename)

    with open(file_path, "wb") as file_object:
        shutil.copyfileobj(image.file, file_object)

    return filename


reports = []


def find_matches(lost_report):
    matches = []

    for report in reports:
        if report["status"] != "found":
            continue

        lost_name = lost_report["item_name"].lower()
        found_name = report["item_name"].lower()

        if (
            lost_name in found_name
            or found_name in lost_name
        ):
            if report["location"].lower() == lost_report["location"].lower():
                matches.append(report)

    return matches

            

class ItemReport(BaseModel):
    item_name: str = Field(min_length=1, max_length=100)
    description: str = Field(min_length=1)
    location: str = Field(min_length=1, max_length=150)
    status: Literal["lost", "found"]

@app.get("/")
def home():
    return FileResponse("static/index.html")




    

def normalize_location(location):
    location = location.lower().strip()

    for prefix in ["in the ", "at the ", "in ", "at "]:
        if location.startswith(prefix):
            location = location[len(prefix):]
            break

    return location




def text_similarity(text1, text2):
    embeddings = model.encode([text1, text2])

    score = cosine_similarity(
        [embeddings[0]],
        [embeddings[1]]
    )[0][0]

    return float(score)


def normalize_location(location):
    location = location.lower().strip()

    for prefix in ["in the ", "at the ", "in ", "at "]:
        if location.startswith(prefix):
            location = location[len(prefix):]
            break

    return location



def is_matching_item(item1, item2):
    # 1. Compare item names
    name_score = text_similarity(
        item1["item_name"],
        item2["item_name"]
    )

    # 2. Compare descriptions
    description_score = text_similarity(
        item1["description"],
        item2["description"]
    )

    # 3. Give more importance to the item name
    combined_score = (
        0.7 * name_score
        + 0.3 * description_score
    )

    # 4. Normalize locations
    location1 = normalize_location(item1["location"])
    location2 = normalize_location(item2["location"])

    # 5. Check location
    location_matches = location1 == location2

    # 6. Require both name similarity and overall similarity
    return (
        name_score >= 0.50
        and combined_score >= 0.60
        and location_matches
    )




@app.post("/report_item")
def create_report(
    item_name: str = Form(...),
    description: str = Form(...),
    location: str = Form(...),
    status: Literal["lost", "found"] = Form(...),
    image: UploadFile | None = File(None)
):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        # 1. Check whether an identical report already exists
        duplicate_query = """
        SELECT * FROM reports
        WHERE LOWER(TRIM(item_name)) = LOWER(TRIM(%s))
        AND LOWER(TRIM(description)) = LOWER(TRIM(%s))
        AND LOWER(TRIM(location)) = LOWER(TRIM(%s))
        AND status = %s
        """

        duplicate_values = (
            item_name,
            description,
            location,
            status
        )

        cursor.execute(duplicate_query, duplicate_values)
        duplicate = cursor.fetchone()

        if duplicate:
            raise HTTPException(
                status_code=409,
                detail="This report already exists!"
            )
            
        image_filename = None

        if image:
            image_filename = save_image(image)
        # 1. Save the new report in MySQL
        query = """
        INSERT INTO reports
        (item_name, description, location, status,image_path)
        VALUES (%s, %s, %s, %s, %s)
        """

        values = (
            item_name,
            description,
            location,
            status,
            image_filename
        )

        cursor.execute(query, values)
        connection.commit()

        report = {
    "item_name": item_name,
    "description": description,
    "location": location,
    "status": status,
    "image_path": image_filename
}

        report["id"] = cursor.lastrowid

        # 2. Find matching lost reports when a found item is submitted
        matches = []

        if report["status"] == "found":
            cursor.execute(
                "SELECT * FROM reports WHERE status = %s AND id != %s",
                ("lost", report["id"])
            )

            existing_reports = cursor.fetchall()

            
            for existing_report in existing_reports:
                if is_matching_item(existing_report, report):
                    matches.append(existing_report)

        # 3. Return the report and matching lost items
        return {
            "message": "Report submitted successfully!",
            "report": report,
            "matching_lost_items": matches
        }

    
    except HTTPException:
        connection.rollback()
        raise

    except Exception:
        connection.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to save or match report"
        )


    finally:
        cursor.close()
        connection.close()





@app.get("/report_items")
def get_reports():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("SELECT * FROM reports ORDER BY id")
        reports = cursor.fetchall()

        # Keep only unique-looking reports for homepage display
        unique_reports = []

        for report in reports:
            duplicate = False

            for existing_report in unique_reports:

                # Lost and found reports must remain separate
                if existing_report["status"] != report["status"]:
                    continue

                # Compare semantic meaning and location
                if is_matching_item(existing_report, report):
                    duplicate = True
                    break

            if not duplicate:
                unique_reports.append(report)

        return unique_reports

    finally:
        
        cursor.close()
        connection.close()




@app.get("/report_items/{report_id}")
def get_report(report_id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM reports WHERE id = %s",
            (report_id,)
        )

        report = cursor.fetchone()

        if report is None:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        return report

    finally:
        cursor.close()
        connection.close()





@app.get("/matches/{report_id}")
def get_matches(report_id: int):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM reports WHERE id = %s",
            (report_id,)
        )
        lost_report = cursor.fetchone()

        if lost_report is None:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        if lost_report["status"] != "lost":
            raise HTTPException(
                status_code=400,
                detail="Matches can only be searched for lost items"
            )

        cursor.execute(
            "SELECT * FROM reports WHERE status = %s AND id != %s",
            ("found", report_id)
        )
        found_reports = cursor.fetchall()

        
        matches = []

        for report in found_reports:
            if is_matching_item(lost_report, report):
                matches.append(report)



        return {
            "lost_item": lost_report,
            "matching_found_items": matches
        }

    finally:
        cursor.close()
        connection.close()



@app.put("/report_items/{report_id}")
def update_report(report_id: int, report: ItemReport):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT id FROM reports WHERE id = %s",
            (report_id,)
        )

        existing_report = cursor.fetchone()

        if existing_report is None:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        cursor.execute(
            """
            UPDATE reports
            SET item_name = %s,
                description = %s,
                location = %s,
                status = %s
            WHERE id = %s
            """,
            (
                report.item_name,
                report.description,
                report.location,
                report.status,
                report_id
            )
        )

        connection.commit()

        return {
            "message": "Report updated successfully!",
            "report_id": report_id,
            "updated_report": report.model_dump()
        }

    finally:
        cursor.close()
        connection.close()


class ReportUpdate(BaseModel):
    item_name: str | None = None
    description: str | None = None
    location: str | None = None
    status: Literal["lost", "found"] | None = None


@app.patch("/report_items/{report_id}")
def patch_report(report_id: int, report: ReportUpdate):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM reports WHERE id = %s",
            (report_id,)
        )
        existing_report = cursor.fetchone()

        if existing_report is None:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        updates = report.model_dump(exclude_unset=True)

        if not updates:
            raise HTTPException(
                status_code=400,
                detail="No fields provided for update"
            )

        allowed_fields = {
            "item_name", "description", "location", "status"
        }

        for field in updates:
            if field not in allowed_fields:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid field"
                )

        set_clause = ", ".join(
            f"{field} = %s" for field in updates
        )
        values = list(updates.values()) + [report_id]

        cursor.execute(
            f"UPDATE reports SET {set_clause} WHERE id = %s",
            values
        )
        connection.commit()

        return {
            "message": "Report updated successfully!",
            "report_id": report_id,
            "updated_fields": updates
        }

    finally:
        cursor.close()
        connection.close()


@app.delete("/report_items/{report_id}")
def delete_report(report_id: int):
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            "SELECT id FROM reports WHERE id = %s",
            (report_id,)
        )

        existing_report = cursor.fetchone()

        if existing_report is None:
            raise HTTPException(
                status_code=404,
                detail="Report not found"
            )

        cursor.execute(
            "DELETE FROM reports WHERE id = %s",
            (report_id,)
        )

        connection.commit()

        return {
            "message": "Report deleted successfully!",
            "report_id": report_id
        }

    finally:
        cursor.close()
        connection.close()
        
        

@app.post("/send_request/{report_id}")
def send_request(
    report_id: int,
    found_location: str = Form(...),
    found_time: str = Form(""),
    current_location: str = Form(...),
    description: str = Form(...),
    handover_option: str = Form("claim_request"),
    photo: UploadFile = File(None)
):
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            "SELECT * FROM reports WHERE id = %s AND status = 'lost'",
            (report_id,)
        )

        report = cursor.fetchone()

        if report is None:
            raise HTTPException(
                status_code=404,
                detail="Lost item report not found"
            )

        photo_path = save_image(photo) if photo else None

        query = """
            INSERT INTO requests
            (report_id, found_location, found_time,
             current_location, description, photo,handover_option)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

        cursor.execute(
            query,
            (report_id, found_location, found_time,
             current_location, description, photo_path, handover_option)
        )

        connection.commit()

        return {
            "message": "Claim request submitted successfully!",
            "request_id": cursor.lastrowid,
            "report_id": report_id,
            "status": "pending"
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(error))

    finally:
        cursor.close()
        connection.close()
        
        
        # Get claim requests for a particular lost item
@app.get("/requests/{report_id}")
def get_claim_requests(report_id: int):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT *
            FROM requests
            WHERE report_id = %s
            ORDER BY created_at DESC
            """,
            (report_id,)
        )

        requests = cursor.fetchall()

        return {
            "report_id": report_id,
            "total_requests": len(requests),
            "requests": requests
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )

    finally:
        cursor.close()
        connection.close()
        
    
# Accept or Reject a Claim Request

@app.put("/requests/{request_id}/{action}")
def update_claim_request(request_id: int, action: str):

    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        action = action.lower()

        if action not in ["accept", "reject"]:
            raise HTTPException(
                status_code=400,
                detail="Action must be accept or reject"
            )

        # Continue with your existing code below...



        # Get the claim request
        cursor.execute(
            "SELECT * FROM requests WHERE id = %s",
            (request_id,)
        )
        claim_request = cursor.fetchone()

        if claim_request is None:
            raise HTTPException(
                status_code=404,
                detail="Claim request not found"
            )

        if claim_request["status"] != "pending":
            raise HTTPException(
                status_code=400,
                detail="This request has already been processed"
            )

        # Update the claim request status
        new_status = "accepted" if action == "accept" else "rejected"

        cursor.execute(
            "UPDATE requests SET status = %s WHERE id = %s",
            (new_status, request_id)
        )

        # If accepted, mark the lost item as returned
        if action == "accept":
            report_id = claim_request["report_id"]

            cursor.execute(
                "UPDATE reports SET status = 'returned' WHERE id = %s",
                (report_id,)
            )

            # Reject other pending requests for this item
            cursor.execute(
                """
                UPDATE requests
                SET status = 'rejected'
                WHERE report_id = %s
                AND id != %s
                AND status = 'pending'
                """,
                (report_id, request_id)
            )

        connection.commit()

        return {
            "message": f"Claim request {new_status} successfully!",
            "request_id": request_id,
            "status": new_status
        }

    except HTTPException:
        connection.rollback()
        raise

    except Exception as error:
        connection.rollback()
        raise HTTPException(status_code=500, detail=str(error))

    finally:
        cursor.close()
        connection.close()

