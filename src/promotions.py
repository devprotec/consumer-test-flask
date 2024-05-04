from datetime import datetime
from .models import promotions
import uuid
import datetime
from flask import jsonify
from bson import json_util
import json

class Promotions:
    """
    Entry for a promotion Record. Contains the following fields:
        - id: Unique identifier for the record.
        - name: Name of the promotion.
        - description: Description of the promotion.
        - start_time: Start date of the promotion.
        - end_time: End date of the promotion.
        - discount_rate: Discount rate of the promotion (rate from 1 to 100%).
        - message: short promo/marketing message on booking page tooltip to explain discount or promo
        - countries: List of countries where the promotion is available.
        - creator: The admin who created the promotion.
        - creation_timestamp: Date the promotion was created.
        - enabled: Boolean indicating if promotion is currently active
    """

    @staticmethod
    def retrieve_promotion_by_uuid(promo_id):
        """
        Retrieve a promotion record from the database.
        """
        my_query = {"id": promo_id}
        promo = promotions.find_one(my_query)
        if promo is None:
            return jsonify({"error": "Promotion not found"}), 401
        return promo

    @staticmethod
    def delete_promotion(promo_id):
        """
        Delete a promotion record from the database.
        """
        my_query = {"id": promo_id}
        deleted_promotion = promotions.delete_one(my_query)
        if deleted_promotion.deleted_count == 1:
            return jsonify({"success": "Promotion deleted successfully."})
        return jsonify({"error": "Promotion not found."})

    @staticmethod
    def update_promotion(promo_id, data):
        """
        Update a promotion record in the database.
        """
        my_query = {"id": promo_id}
        updated_promo = promotions.find_one_and_update(
            my_query, {"$set": data})
        new_promo = promotions.find_one(my_query)
        print(new_promo)
        if updated_promo:
            return json.loads(json_util.dumps({"result": new_promo})), 200

        return jsonify({"error": "Failed to update promotion. Try again, please."}), 401

    def create_promotion(self, data):
        """
        Create a promotion record.
        """

        promo = {
            "id": uuid.uuid4().hex,
            "creation_timestamp": datetime.datetime.now(),
            **data
        }

        new_promo = promotions.insert_one(promo)

        if new_promo:
            inserted_promo = self.retrieve_promotion_by_uuid(promo["id"])
            return json.loads(json_util.dumps({"result": inserted_promo})), 200
        return jsonify({"error": "Failed to add promotion. Try again, please."}), 401