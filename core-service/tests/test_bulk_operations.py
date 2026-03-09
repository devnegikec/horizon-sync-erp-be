"""Tests for bulk import and export operations"""

import json
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.core.bulk_operations import (
    BulkImportValidator,
    FileGenerator,
    FileParser,
)
from app.models.bulk_import_job import BulkImportJobStatus
from app.models.item import Item
from app.repositories.bulk_export_repository import BulkExportRepository
from app.repositories.bulk_import_repository import BulkImportRepository
from app.services.bulk_export_service import BulkExportService
from app.services.bulk_import_service import BulkImportService

# ==================== VALIDATOR TESTS ====================


class TestBulkImportValidator:
    """Test bulk import validator"""

    def test_validate_file_size_valid(self):
        """Test valid file size"""
        is_valid, error = BulkImportValidator.validate_file_size(1024 * 1024)
        assert is_valid is True
        assert error is None

    def test_validate_file_size_too_large(self):
        """Test file size exceeds limit"""
        is_valid, error = BulkImportValidator.validate_file_size(60 * 1024 * 1024)
        assert is_valid is False
        assert error is not None

    def test_validate_file_format_csv(self):
        """Test CSV format validation"""
        is_valid, error = BulkImportValidator.validate_file_format("text/csv", "csv")
        assert is_valid is True

    def test_validate_file_format_xlsx(self):
        """Test XLSX format validation"""
        is_valid, error = BulkImportValidator.validate_file_format(
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
        )
        assert is_valid is True

    def test_validate_file_format_invalid(self):
        """Test invalid format"""
        is_valid, error = BulkImportValidator.validate_file_format("text/csv", "pdf")
        assert is_valid is False
        assert error is not None

    def test_validate_row_valid(self):
        """Test valid row"""
        row = {"item_code": "ITEM001", "item_name": "Test Item"}
        is_valid, errors = BulkImportValidator.validate_row(row, 1)
        assert is_valid is True
        assert len(errors) == 0

    def test_validate_row_missing_required_field(self):
        """Test row with missing required field"""
        row = {"item_code": "ITEM001"}  # Missing item_name
        is_valid, errors = BulkImportValidator.validate_row(row, 1)
        assert is_valid is False
        assert len(errors) > 0

    def test_validate_row_item_code_too_long(self):
        """Test item code exceeds max length"""
        row = {"item_code": "X" * 101, "item_name": "Test Item"}
        is_valid, errors = BulkImportValidator.validate_row(row, 1)
        assert is_valid is False


# ==================== FILE PARSER TESTS ====================


class TestFileParser:
    """Test file parser"""

    def test_parse_csv(self):
        """Test CSV parsing"""
        csv_content = b"item_code,item_name\nITEM001,Test Item\nITEM002,Another Item"
        rows = FileParser.parse_csv(csv_content)
        assert len(rows) == 2
        assert rows[0]["item_code"] == "ITEM001"
        assert rows[0]["item_name"] == "Test Item"

    def test_parse_csv_invalid(self):
        """Test invalid CSV"""
        with pytest.raises(ValueError):
            FileParser.parse_csv(b"\xff\xfe Invalid UTF-8")

    def test_parse_json(self):
        """Test JSON parsing"""
        json_data = {"items": [{"item_code": "ITEM001", "item_name": "Test"}]}
        json_content = json.dumps(json_data).encode("utf-8")
        rows = FileParser.parse_json(json_content)
        assert len(rows) == 1
        assert rows[0]["item_code"] == "ITEM001"

    def test_parse_json_array(self):
        """Test JSON array parsing"""
        json_data = [{"item_code": "ITEM001", "item_name": "Test"}]
        json_content = json.dumps(json_data).encode("utf-8")
        rows = FileParser.parse_json(json_content)
        assert len(rows) == 1


# ==================== FILE GENERATOR TESTS ====================


class TestFileGenerator:
    """Test file generator"""

    def test_generate_csv(self):
        """Test CSV generation"""
        data = [
            {"item_code": "ITEM001", "item_name": "Test Item"},
            {"item_code": "ITEM002", "item_name": "Another Item"},
        ]
        csv_content = FileGenerator.generate_csv(data)
        assert b"item_code" in csv_content
        assert b"ITEM001" in csv_content

    def test_generate_json(self):
        """Test JSON generation"""
        data = [{"item_code": "ITEM001", "item_name": "Test Item"}]
        json_content = FileGenerator.generate_json(data)
        parsed = json.loads(json_content.decode("utf-8"))
        assert "items" in parsed
        assert len(parsed["items"]) == 1

    def test_generate_csv_empty(self):
        """Test generating CSV from empty data"""
        csv_content = FileGenerator.generate_csv([])
        assert csv_content == b""


# ==================== REPOSITORY TESTS ====================


class TestBulkImportRepository:
    """Test bulk import repository"""

    def test_create_job(self, db_session: Session):
        """Test creating import job"""
        repo = BulkImportRepository(db_session)
        org_id = uuid4()
        user_id = uuid4()

        job = repo.create_job(
            organization_id=org_id,
            created_by_id=user_id,
            file_name="test.csv",
            mime_type="text/csv",
        )

        assert job.id is not None
        assert job.organization_id == org_id
        assert job.status == BulkImportJobStatus.PENDING

    def test_get_job_by_id(self, db_session: Session):
        """Test getting job by ID"""
        repo = BulkImportRepository(db_session)
        org_id = uuid4()
        user_id = uuid4()

        job = repo.create_job(
            organization_id=org_id,
            created_by_id=user_id,
            file_name="test.csv",
            mime_type="text/csv",
        )

        retrieved = repo.get_job_by_id(job.id)
        assert retrieved is not None
        assert retrieved.id == job.id

    def test_update_job_status(self, db_session: Session):
        """Test updating job status"""
        repo = BulkImportRepository(db_session)
        org_id = uuid4()
        user_id = uuid4()

        job = repo.create_job(
            organization_id=org_id,
            created_by_id=user_id,
            file_name="test.csv",
            mime_type="text/csv",
        )

        updated = repo.update_job_status(
            job.id, BulkImportJobStatus.COMPLETED, "Import completed"
        )
        assert updated.status == BulkImportJobStatus.COMPLETED
        assert updated.summary == "Import completed"


class TestBulkExportRepository:
    """Test bulk export repository"""

    def test_create_job(self, db_session: Session):
        """Test creating export job"""
        repo = BulkExportRepository(db_session)
        org_id = uuid4()
        user_id = uuid4()

        job = repo.create_job(
            organization_id=org_id,
            created_by_id=user_id,
            file_name="items_export",
            file_format="csv",
        )

        assert job.id is not None
        assert job.file_format == "csv"


# ==================== INTEGRATION TESTS ====================


class TestBulkImportService:
    """Test bulk import service"""

    @pytest.mark.asyncio
    async def test_create_import_job(self, db_session: Session):
        """Test creating import job via service"""
        service = BulkImportService(db_session)
        org_id = uuid4()
        user_id = uuid4()

        job = await service.create_import_job(
            organization_id=org_id,
            created_by_id=user_id,
            file_name="test.csv",
            mime_type="text/csv",
        )

        assert job.id is not None
        assert job.status == BulkImportJobStatus.PENDING

    @pytest.mark.asyncio
    async def test_process_import_valid_csv(self, db_session: Session):
        """Test processing valid CSV import"""
        service = BulkImportService(db_session)
        org_id = uuid4()
        user_id = uuid4()

        # Create import job
        job = await service.create_import_job(
            organization_id=org_id,
            created_by_id=user_id,
            file_name="test.csv",
            mime_type="text/csv",
        )

        # Create sample CSV
        csv_data = b"item_code,item_name\nITEM001,Test Item\nITEM002,Another Item"

        # Process import
        result = await service.process_import(
            job_id=job.id,
            organization_id=org_id,
            file_content=csv_data,
            file_format="csv",
        )

        assert result["success"] is True
        assert result["successful_rows"] == 2
        assert result["failed_rows"] == 0

        # Verify items were created
        items = db_session.query(Item).filter(Item.organization_id == org_id).all()
        assert len(items) == 2


class TestBulkExportService:
    """Test bulk export service"""

    @pytest.mark.asyncio
    async def test_create_export_job(self, db_session: Session):
        """Test creating export job via service"""
        service = BulkExportService(db_session)
        org_id = uuid4()
        user_id = uuid4()

        job = await service.create_export_job(
            organization_id=org_id,
            created_by_id=user_id,
            file_name="items_export",
            file_format="csv",
        )

        assert job.id is not None
        assert job.file_format == "csv"

    @pytest.mark.asyncio
    async def test_process_export_csv(self, db_session: Session):
        """Test processing export to CSV"""
        service = BulkExportService(db_session)
        org_id = uuid4()
        user_id = uuid4()

        # Create sample items
        for i in range(3):
            item = Item(
                organization_id=org_id,
                item_code=f"ITEM{i + 1:03d}",
                item_name=f"Test Item {i + 1}",
            )
            db_session.add(item)
        db_session.commit()

        # Create export job
        job = await service.create_export_job(
            organization_id=org_id,
            created_by_id=user_id,
            file_name="items_export",
            file_format="csv",
        )

        # Process export
        result = await service.process_export(
            job_id=job.id,
            organization_id=org_id,
            file_format="csv",
        )

        assert result["success"] is True
        assert result["total_rows"] == 3
