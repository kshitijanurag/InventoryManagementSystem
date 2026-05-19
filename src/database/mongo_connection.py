from pymongo import MongoClient
from pymongo.database import Database


class MongoConnectionSingleton:
    _mongo_client_instance: MongoClient | None = None
    _primary_database_name: str = "inventory"

    @classmethod
    def get_client(cls) -> MongoClient:
        if cls._mongo_client_instance is None:
            cls._mongo_client_instance = MongoClient(
                "mongodb://localhost:27017/",
                serverSelectionTimeoutMS=5000,
            )
        return cls._mongo_client_instance

    @classmethod
    def get_database(cls, database_name: str | None = None) -> Database:
        client = cls.get_client()
        resolved_database_name = database_name or cls._primary_database_name
        return client[resolved_database_name]

    @classmethod
    def close_connection(cls) -> None:
        if cls._mongo_client_instance is not None:
            cls._mongo_client_instance.close()
            cls._mongo_client_instance = None


def get_inventory_database() -> Database:
    return MongoConnectionSingleton.get_database("inventory")


def get_analytics_database() -> Database:
    return MongoConnectionSingleton.get_database("inventoryai")
