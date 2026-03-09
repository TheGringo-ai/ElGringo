"""
Database Tools - Database operations for AI agents
===================================================

Capabilities:
- Firebase/Firestore operations
- PostgreSQL operations
- SQLite operations
- Schema design and migrations
- Query execution
"""

import asyncio
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Tool, ToolResult, PermissionManager

logger = logging.getLogger(__name__)


class DatabaseTools(Tool):
    """
    Database management tools for AI-powered development.

    Supports Firestore, PostgreSQL, and SQLite for
    local development and cloud deployment.
    """

    def __init__(
        self,
        permission_manager: Optional[PermissionManager] = None,
        firestore_project: Optional[str] = None,
        firestore_credentials: Optional[str] = None
    ):
        super().__init__(
            name="database",
            description="Database operations (Firestore, PostgreSQL, SQLite)",
            permission_manager=permission_manager,
        )

        self.firestore_project = firestore_project or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.firestore_credentials = firestore_credentials or os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        self._firestore_client = None
        self._postgres_conn = None

        # Register operations
        # Firestore operations
        self.register_operation("firestore_get", self._firestore_get, "Get Firestore document", requires_permission=False)
        self.register_operation("firestore_set", self._firestore_set, "Set Firestore document")
        self.register_operation("firestore_update", self._firestore_update, "Update Firestore document")
        self.register_operation("firestore_delete", self._firestore_delete, "Delete Firestore document")
        self.register_operation("firestore_query", self._firestore_query, "Query Firestore collection", requires_permission=False)
        self.register_operation("firestore_list", self._firestore_list, "List Firestore collections", requires_permission=False)

        # SQLite operations
        self.register_operation("sqlite_query", self._sqlite_query, "Execute SQLite query")
        self.register_operation("sqlite_execute", self._sqlite_execute, "Execute SQLite statement")
        self.register_operation("sqlite_schema", self._sqlite_schema, "Get SQLite schema", requires_permission=False)
        self.register_operation("sqlite_tables", self._sqlite_tables, "List SQLite tables", requires_permission=False)

        # PostgreSQL operations
        self.register_operation("postgres_query", self._postgres_query, "Execute PostgreSQL query")
        self.register_operation("postgres_execute", self._postgres_execute, "Execute PostgreSQL statement")
        self.register_operation("postgres_schema", self._postgres_schema, "Get PostgreSQL schema", requires_permission=False)

        # Schema design
        self.register_operation("design_schema", self._design_schema, "Design database schema", requires_permission=False)
        self.register_operation("generate_migration", self._generate_migration, "Generate migration SQL")

    def _get_firestore(self):
        """Get or create Firestore client"""
        if self._firestore_client is None:
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore

                if not firebase_admin._apps:
                    if self.firestore_credentials and os.path.exists(self.firestore_credentials):
                        cred = credentials.Certificate(self.firestore_credentials)
                        firebase_admin.initialize_app(cred, {
                            'projectId': self.firestore_project
                        })
                    else:
                        # Try default credentials
                        firebase_admin.initialize_app()

                self._firestore_client = firestore.client()
            except ImportError:
                logger.warning("firebase-admin not installed. Firestore operations unavailable.")
                return None
            except Exception as e:
                logger.error(f"Failed to initialize Firestore: {e}")
                return None

        return self._firestore_client

    # Firestore operations
    def _firestore_get(
        self,
        collection: str,
        document_id: str
    ) -> ToolResult:
        """Get a Firestore document"""
        try:
            db = self._get_firestore()
            if db is None:
                return ToolResult(success=False, output=None, error="Firestore not available")

            doc_ref = db.collection(collection).document(document_id)
            doc = doc_ref.get()

            if doc.exists:
                return ToolResult(
                    success=True,
                    output=doc.to_dict(),
                    metadata={"collection": collection, "id": document_id}
                )
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=f"Document not found: {collection}/{document_id}"
                )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _firestore_set(
        self,
        collection: str,
        document_id: str,
        data: Dict[str, Any],
        merge: bool = False
    ) -> ToolResult:
        """Set a Firestore document"""
        try:
            db = self._get_firestore()
            if db is None:
                return ToolResult(success=False, output=None, error="Firestore not available")

            doc_ref = db.collection(collection).document(document_id)
            doc_ref.set(data, merge=merge)

            return ToolResult(
                success=True,
                output=f"Document {collection}/{document_id} saved",
                metadata={"collection": collection, "id": document_id, "merge": merge}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _firestore_update(
        self,
        collection: str,
        document_id: str,
        data: Dict[str, Any]
    ) -> ToolResult:
        """Update a Firestore document"""
        try:
            db = self._get_firestore()
            if db is None:
                return ToolResult(success=False, output=None, error="Firestore not available")

            doc_ref = db.collection(collection).document(document_id)
            doc_ref.update(data)

            return ToolResult(
                success=True,
                output=f"Document {collection}/{document_id} updated",
                metadata={"collection": collection, "id": document_id}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _firestore_delete(
        self,
        collection: str,
        document_id: str
    ) -> ToolResult:
        """Delete a Firestore document"""
        try:
            db = self._get_firestore()
            if db is None:
                return ToolResult(success=False, output=None, error="Firestore not available")

            doc_ref = db.collection(collection).document(document_id)
            doc_ref.delete()

            return ToolResult(
                success=True,
                output=f"Document {collection}/{document_id} deleted",
                metadata={"collection": collection, "id": document_id}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _firestore_query(
        self,
        collection: str,
        where: Optional[List[tuple]] = None,
        order_by: Optional[str] = None,
        limit: int = 100
    ) -> ToolResult:
        """Query a Firestore collection"""
        try:
            db = self._get_firestore()
            if db is None:
                return ToolResult(success=False, output=None, error="Firestore not available")

            query = db.collection(collection)

            if where:
                for field, op, value in where:
                    query = query.where(field, op, value)

            if order_by:
                query = query.order_by(order_by)

            query = query.limit(limit)
            docs = query.stream()

            results = []
            for doc in docs:
                results.append({"id": doc.id, **doc.to_dict()})

            return ToolResult(
                success=True,
                output=results,
                metadata={"collection": collection, "count": len(results)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _firestore_list(self) -> ToolResult:
        """List Firestore collections"""
        try:
            db = self._get_firestore()
            if db is None:
                return ToolResult(success=False, output=None, error="Firestore not available")

            collections = [col.id for col in db.collections()]

            return ToolResult(
                success=True,
                output=collections,
                metadata={"count": len(collections)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    # SQLite operations
    def _sqlite_query(
        self,
        database: str,
        query: str,
        params: Optional[tuple] = None
    ) -> ToolResult:
        """Execute SQLite query and return results"""
        try:
            db_path = Path(database).expanduser().resolve()
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)

            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            conn.close()

            return ToolResult(
                success=True,
                output=results,
                metadata={"database": str(db_path), "count": len(results)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _sqlite_execute(
        self,
        database: str,
        statement: str,
        params: Optional[tuple] = None
    ) -> ToolResult:
        """Execute SQLite statement (INSERT, UPDATE, DELETE, CREATE)"""
        try:
            db_path = Path(database).expanduser().resolve()
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            if params:
                cursor.execute(statement, params)
            else:
                cursor.execute(statement)

            conn.commit()
            affected = cursor.rowcount
            conn.close()

            return ToolResult(
                success=True,
                output=f"Statement executed. Rows affected: {affected}",
                metadata={"database": str(db_path), "rows_affected": affected}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _sqlite_schema(self, database: str) -> ToolResult:
        """Get SQLite database schema"""
        try:
            db_path = Path(database).expanduser().resolve()
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' ORDER BY name")
            schemas = [row[0] for row in cursor.fetchall() if row[0]]
            conn.close()

            return ToolResult(
                success=True,
                output="\n\n".join(schemas),
                metadata={"database": str(db_path)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _sqlite_tables(self, database: str) -> ToolResult:
        """List SQLite tables"""
        try:
            db_path = Path(database).expanduser().resolve()
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]
            conn.close()

            return ToolResult(
                success=True,
                output=tables,
                metadata={"database": str(db_path), "count": len(tables)}
            )

        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    # PostgreSQL operations
    async def _run_psql(
        self,
        query: str,
        database: str,
        host: str = "localhost",
        port: int = 5432,
        user: Optional[str] = None,
        password: Optional[str] = None
    ) -> ToolResult:
        """Execute PostgreSQL query via psql"""
        try:
            env = os.environ.copy()
            if password:
                env["PGPASSWORD"] = password

            cmd = [
                "psql",
                "-h", host,
                "-p", str(port),
                "-d", database,
                "-t",  # Tuples only
                "-A",  # Unaligned output
                "-c", query
            ]
            if user:
                cmd.extend(["-U", user])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=60
            )

            if process.returncode == 0:
                return ToolResult(
                    success=True,
                    output=stdout.decode().strip(),
                    metadata={"database": database}
                )
            else:
                return ToolResult(
                    success=False,
                    output=None,
                    error=stderr.decode().strip()
                )

        except FileNotFoundError:
            return ToolResult(success=False, output=None, error="psql not found. Install PostgreSQL client.")
        except Exception as e:
            return ToolResult(success=False, output=None, error=str(e))

    def _postgres_query(
        self,
        query: str,
        database: str,
        host: str = "localhost",
        port: int = 5432,
        user: Optional[str] = None,
        password: Optional[str] = None
    ) -> ToolResult:
        """Execute PostgreSQL query"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_psql(query, database, host, port, user, password)
        )

    def _postgres_execute(
        self,
        statement: str,
        database: str,
        host: str = "localhost",
        port: int = 5432,
        user: Optional[str] = None,
        password: Optional[str] = None
    ) -> ToolResult:
        """Execute PostgreSQL statement"""
        return asyncio.get_event_loop().run_until_complete(
            self._run_psql(statement, database, host, port, user, password)
        )

    def _postgres_schema(
        self,
        database: str,
        host: str = "localhost",
        port: int = 5432,
        user: Optional[str] = None,
        password: Optional[str] = None
    ) -> ToolResult:
        """Get PostgreSQL schema"""
        query = """
        SELECT table_name, column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_name, ordinal_position;
        """
        return asyncio.get_event_loop().run_until_complete(
            self._run_psql(query, database, host, port, user, password)
        )

    # Schema design helpers
    def _design_schema(
        self,
        description: str,
        database_type: str = "firestore"
    ) -> ToolResult:
        """Generate schema design based on description (AI-assisted)"""
        # This would typically call an AI model to design the schema
        # For now, return a template
        if database_type == "firestore":
            template = {
                "description": description,
                "collections": {
                    "example": {
                        "fields": {
                            "id": "string (auto)",
                            "created_at": "timestamp",
                            "updated_at": "timestamp"
                        },
                        "subcollections": []
                    }
                },
                "indexes": [],
                "security_rules": "// Add security rules"
            }
        else:
            template = {
                "description": description,
                "tables": {
                    "example": {
                        "columns": [
                            {"name": "id", "type": "SERIAL PRIMARY KEY"},
                            {"name": "created_at", "type": "TIMESTAMP DEFAULT NOW()"},
                            {"name": "updated_at", "type": "TIMESTAMP DEFAULT NOW()"}
                        ],
                        "indexes": [],
                        "constraints": []
                    }
                }
            }

        return ToolResult(
            success=True,
            output=template,
            metadata={"database_type": database_type, "note": "Template - customize as needed"}
        )

    def _generate_migration(
        self,
        from_schema: Dict[str, Any],
        to_schema: Dict[str, Any],
        database_type: str = "postgresql"
    ) -> ToolResult:
        """Generate migration SQL between schemas"""
        # Basic migration generation
        migrations = []

        if database_type == "postgresql":
            # Compare tables
            from_tables = set(from_schema.get("tables", {}).keys())
            to_tables = set(to_schema.get("tables", {}).keys())

            # New tables
            for table in to_tables - from_tables:
                cols = to_schema["tables"][table].get("columns", [])
                col_defs = ", ".join([f'{c["name"]} {c["type"]}' for c in cols])
                migrations.append(f"CREATE TABLE {table} ({col_defs});")

            # Dropped tables
            for table in from_tables - to_tables:
                migrations.append(f"DROP TABLE {table};")

        return ToolResult(
            success=True,
            output="\n".join(migrations) if migrations else "-- No migrations needed",
            metadata={"database_type": database_type, "migration_count": len(migrations)}
        )


    def get_capabilities(self) -> List[Dict[str, str]]:
        """Return list of Database tool capabilities."""
        return [
            {"name": "firestore_get", "description": "Get Firestore document"},
            {"name": "firestore_set", "description": "Set Firestore document"},
            {"name": "firestore_query", "description": "Query Firestore collection"},
            {"name": "sqlite_query", "description": "Execute SQLite query"},
            {"name": "sqlite_execute", "description": "Execute SQLite statement"},
            {"name": "postgres_query", "description": "Execute PostgreSQL query"},
            {"name": "design_schema", "description": "Design database schema"},
        ]


# Convenience function
def create_database_tools(
    firestore_project: Optional[str] = None,
    firestore_credentials: Optional[str] = None
) -> DatabaseTools:
    """Create Database tools instance"""
    return DatabaseTools(
        firestore_project=firestore_project,
        firestore_credentials=firestore_credentials
    )
