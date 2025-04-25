from flask import request, jsonify
from werkzeug.utils import secure_filename
import os
import uuid
import time
import glob
from config import db
from .model import ObjectDetector

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
RESULT_FOLDER = "results"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULT_FOLDER, exist_ok=True)

detector = None


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def initialize_detector():
    global detector
    if detector is None:
        detector = ObjectDetector()
    return detector


def cleanup_old_files(directory, max_age_hours=24):
    now = time.time()
    max_age_seconds = max_age_hours * 3600

    files = glob.glob(os.path.join(directory, "*"))

    for file_path in files:
        if os.path.isfile(file_path):
            file_age = now - os.path.getmtime(file_path)

            if file_age > max_age_seconds:
                try:
                    os.remove(file_path)
                    print(f"Deleted old file: {file_path}")
                except Exception as e:
                    print(f"Error deleting {file_path}: {str(e)}")


def process_image():
    cleanup_old_files(UPLOAD_FOLDER)
    cleanup_old_files(RESULT_FOLDER)

    try:
        detector = initialize_detector()
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500

    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        filepath = os.path.join(UPLOAD_FOLDER, unique_filename)
        file.save(filepath)

        try:
            confidence_threshold = float(
                request.headers.get("X-Confidence-Threshold", 0.5)
            )
            detections = detector.detect(filepath, confidence_threshold)

            result_filename = f"result_{unique_filename}"
            result_path = os.path.join(RESULT_FOLDER, result_filename)
            annotated_path = detector.annotate_image(filepath, result_path, detections)

            mapped_results = map_to_inventory_categories(detections)

            return (
                jsonify(
                    {
                        "success": True,
                        "detections": detections,
                        "annotated_image": f"/api/images/{result_filename}",
                        "category_suggestions": mapped_results["suggestions"],
                        "unmapped_objects": mapped_results["unmapped_objects"],
                    }
                ),
                200,
            )

        except Exception as e:
            print(f"Processing error: {str(e)}")
            import traceback

            print(traceback.format_exc())
            return jsonify({"error": f"Processing error: {str(e)}"}), 500

    return jsonify({"error": "File type not allowed"}), 400


def map_to_inventory_categories(detections):
    """Map detected objects to inventory categories and find existing items."""
    cursor = None
    try:
        cursor = db.connection.cursor()

        cursor.execute(
            """
            SELECT om.object_name, c.category_name, om.category_id
            FROM object_mappings om
            JOIN categories c ON om.category_id = c.category_id
        """
        )
        object_mappings = {
            row[0]: {"category_name": row[1], "category_id": row[2]}
            for row in cursor.fetchall()
        }

        suggestions = []
        unmapped_objects = []
        detection_counts = {}
        category_ids_found = set()

        for detection in detections:
            object_class = detection["class"]
            detection_counts[object_class] = detection_counts.get(object_class, 0) + 1

            if object_class in object_mappings:
                category_id = object_mappings[object_class]["category_id"]
                category_ids_found.add(category_id)
            else:
                unmapped_objects.append(object_class)

        existing_items_by_category = {}
        if category_ids_found:
            placeholders = ", ".join(["%s"] * len(category_ids_found))
            query = f"SELECT item_id, name, quantity, category_id FROM items WHERE category_id IN ({placeholders})"
            cursor.execute(query, tuple(category_ids_found))
            for item_row in cursor.fetchall():
                cat_id = item_row[3]
                if cat_id not in existing_items_by_category:
                    existing_items_by_category[cat_id] = []
                existing_items_by_category[cat_id].append(
                    {
                        "item_id": item_row[0],
                        "name": item_row[1],
                        "quantity": item_row[2],
                    }
                )

        processed_object_classes = set()
        for detection in detections:
            object_class = detection["class"]
            if (
                object_class in object_mappings
                and object_class not in processed_object_classes
            ):
                mapping_info = object_mappings[object_class]
                category_id = mapping_info["category_id"]
                suggestions.append(
                    {
                        "detected_object": object_class,
                        "suggested_category": mapping_info["category_name"],
                        "category_id": category_id,
                        "confidence": detection["confidence"],
                        "count": detection_counts.get(object_class, 0),
                        "existing_items_in_category": existing_items_by_category.get(
                            category_id, []
                        ),
                    }
                )
                processed_object_classes.add(object_class)

        unmapped_objects = list(set(unmapped_objects))

        return {"suggestions": suggestions, "unmapped_objects": unmapped_objects}

    except Exception as e:
        print(f"Error in category mapping: {str(e)}")
        import traceback

        print(traceback.format_exc())
        return {"suggestions": [], "unmapped_objects": []}
    finally:
        if cursor:
            cursor.close()
