"""Tests for file importers (CSV, Excel, QIF, OFX)."""

import datetime
import hashlib
import io
import pathlib

import openpyxl
import pytest

pytestmark = pytest.mark.asyncio


# ── ImportedTransaction schema ──────────────────────────────────


def test_imported_transaction_required_fields():
    from budgie.importers.base import ImportedTransaction

    txn = ImportedTransaction(
        date=datetime.date(2026, 1, 15),
        amount=-5050,
        description="Carrefour Market",
    )
    assert txn.date == datetime.date(2026, 1, 15)
    assert txn.amount == -5050
    assert txn.description == "Carrefour Market"
    assert txn.payee_name is None
    assert txn.reference is None
    assert txn.import_hash is not None  # auto-computed


def test_imported_transaction_hash_deterministic():
    """Same inputs always produce the same hash."""
    from budgie.importers.base import ImportedTransaction

    t1 = ImportedTransaction(
        date=datetime.date(2026, 1, 15),
        amount=-5050,
        description="Carrefour",
    )
    t2 = ImportedTransaction(
        date=datetime.date(2026, 1, 15),
        amount=-5050,
        description="Carrefour",
    )
    assert t1.import_hash == t2.import_hash


def test_imported_transaction_hash_differs_on_different_data():
    from budgie.importers.base import ImportedTransaction

    t1 = ImportedTransaction(
        date=datetime.date(2026, 1, 15),
        amount=-5050,
        description="Carrefour",
    )
    t2 = ImportedTransaction(
        date=datetime.date(2026, 1, 16),
        amount=-5050,
        description="Carrefour",
    )
    assert t1.import_hash != t2.import_hash


def test_imported_transaction_with_reference_affects_hash():
    from budgie.importers.base import ImportedTransaction

    t1 = ImportedTransaction(
        date=datetime.date(2026, 1, 15),
        amount=-5050,
        description="Payment",
        reference="REF001",
    )
    t2 = ImportedTransaction(
        date=datetime.date(2026, 1, 15),
        amount=-5050,
        description="Payment",
        reference="REF002",
    )
    assert t1.import_hash != t2.import_hash


# ── CSV importer ────────────────────────────────────────────────


def test_csv_importer_standard_columns():
    """CSV with date, description, amount columns."""
    from budgie.importers.csv_importer import CsvImporter

    csv_content = """date,description,amount
2026-01-15,Carrefour Market,-50.50
2026-01-16,Salaire,2500.00
2026-01-17,EDF,-120.00
"""
    importer = CsvImporter()
    txns = importer.parse(
        io.BytesIO(csv_content.encode()),
        column_map={"date": "date", "description": "description", "amount": "amount"},
        date_format="%Y-%m-%d",
    )
    assert len(txns) == 3
    assert txns[0].amount == -5050  # -50.50 → centimes
    assert txns[0].description == "Carrefour Market"
    assert txns[0].date == datetime.date(2026, 1, 15)
    assert txns[1].amount == 250000  # 2500.00 → centimes
    assert txns[2].amount == -12000


def test_csv_importer_debit_credit_columns():
    """CSV with separate debit and credit columns."""
    from budgie.importers.csv_importer import CsvImporter

    csv_content = """date,libelle,debit,credit
15/01/2026,Carrefour,50.50,
16/01/2026,Virement,,2500.00
"""
    importer = CsvImporter()
    txns = importer.parse(
        io.BytesIO(csv_content.encode()),
        column_map={
            "date": "date",
            "description": "libelle",
            "debit": "debit",
            "credit": "credit",
        },
        date_format="%d/%m/%Y",
    )
    assert len(txns) == 2
    assert txns[0].amount == -5050  # debit → negative
    assert txns[1].amount == 250000  # credit → positive


def test_csv_importer_semicolon_separator():
    from budgie.importers.csv_importer import CsvImporter

    csv_content = """date;libelle;montant
2026-01-15;Loyer;-800.00
"""
    importer = CsvImporter()
    txns = importer.parse(
        io.BytesIO(csv_content.encode()),
        column_map={
            "date": "date",
            "description": "libelle",
            "amount": "montant",
        },
        date_format="%Y-%m-%d",
        separator=";",
    )
    assert len(txns) == 1
    assert txns[0].amount == -80000


def test_csv_importer_skips_empty_rows():
    from budgie.importers.csv_importer import CsvImporter

    csv_content = """date,description,amount
2026-01-15,Carrefour,-50.50

2026-01-17,EDF,-120.00
"""
    importer = CsvImporter()
    txns = importer.parse(
        io.BytesIO(csv_content.encode()),
        column_map={"date": "date", "description": "description", "amount": "amount"},
        date_format="%Y-%m-%d",
    )
    assert len(txns) == 2


def test_csv_importer_optional_payee_column():
    from budgie.importers.csv_importer import CsvImporter

    csv_content = """date,payee,memo,amount
2026-01-15,Carrefour,Weekly shopping,-50.50
"""
    importer = CsvImporter()
    txns = importer.parse(
        io.BytesIO(csv_content.encode()),
        column_map={
            "date": "date",
            "description": "memo",
            "payee": "payee",
            "amount": "amount",
        },
        date_format="%Y-%m-%d",
    )
    assert txns[0].payee_name == "Carrefour"
    assert txns[0].description == "Weekly shopping"


# ── Excel importer ───────────────────────────────────────────────


def test_excel_importer_basic():
    """Excel file with standard columns."""
    from budgie.importers.excel_importer import ExcelImporter

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["date", "description", "amount"])
    ws.append([datetime.date(2026, 1, 15), "Carrefour", -50.50])
    ws.append([datetime.date(2026, 1, 16), "Salaire", 2500.00])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    importer = ExcelImporter()
    txns = importer.parse(
        buf,
        column_map={"date": "date", "description": "description", "amount": "amount"},
    )
    assert len(txns) == 2
    assert txns[0].amount == -5050
    assert txns[0].description == "Carrefour"


def test_excel_importer_string_dates():
    """Excel with date strings instead of date objects."""
    from budgie.importers.excel_importer import ExcelImporter

    wb = openpyxl.Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["Date", "Libellé", "Montant"])
    ws.append(["15/01/2026", "EDF", -120.0])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    importer = ExcelImporter()
    txns = importer.parse(
        buf,
        column_map={"date": "Date", "description": "Libellé", "amount": "Montant"},
        date_format="%d/%m/%Y",
    )
    assert len(txns) == 1
    assert txns[0].amount == -12000
    assert txns[0].date == datetime.date(2026, 1, 15)


# ── QIF importer ────────────────────────────────────────────────


def test_qif_importer_basic():
    from budgie.importers.qif_importer import QifImporter

    qif_content = """!Type:Bank
D01/15/2026
T-50.50
PCarrefour Market
MWeekly groceries
^
D01/16/2026
T2500.00
PSalaire
^
"""
    importer = QifImporter()
    txns = importer.parse(io.BytesIO(qif_content.encode()))
    assert len(txns) == 2
    assert txns[0].amount == -5050
    assert txns[0].payee_name == "Carrefour Market"
    assert txns[0].description == "Weekly groceries"
    assert txns[1].amount == 250000


def test_qif_importer_date_format():
    from budgie.importers.qif_importer import QifImporter

    qif_content = """!Type:Bank
D15/01/2026
T-120.00
PEDF
^
"""
    importer = QifImporter()
    txns = importer.parse(io.BytesIO(qif_content.encode()), date_format="%d/%m/%Y")
    assert len(txns) == 1
    assert txns[0].date == datetime.date(2026, 1, 15)
    assert txns[0].amount == -12000


# ── OFX importer ────────────────────────────────────────────────


def test_ofx_importer_basic():
    from budgie.importers.ofx_importer import OfxImporter

    # Minimal SGML OFX (pre-2.0 banking format)
    ofx_content = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1001
<STATUS><CODE>0<SEVERITY>INFO</STATUS>
<STMTRS>
<CURDEF>EUR
<BANKACCTFROM><BANKID>12345<ACCTID>00001234567<ACCTTYPE>CHECKING</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20260101
<DTEND>20260131
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260115
<TRNAMT>-50.50
<FITID>TXN001
<NAME>Carrefour Market
</STMTTRN>
<STMTTRN>
<TRNTYPE>CREDIT
<DTPOSTED>20260116
<TRNAMT>2500.00
<FITID>TXN002
<NAME>Virement salaire
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""
    importer = OfxImporter()
    txns = importer.parse(io.BytesIO(ofx_content.encode("ascii")))
    assert len(txns) == 2
    assert txns[0].amount == -5050
    assert txns[0].payee_name == "Carrefour Market"
    assert txns[0].date == datetime.date(2026, 1, 15)
    assert txns[0].reference == "TXN001"
    assert txns[0].import_hash is not None
    assert txns[1].amount == 250000


def test_ofx_importer_fitid_as_reference():
    """FITID is used as import reference for deduplication."""
    from budgie.importers.ofx_importer import OfxImporter

    ofx_content = """OFXHEADER:100
DATA:OFXSGML
VERSION:102
SECURITY:NONE
ENCODING:USASCII
CHARSET:1252
COMPRESSION:NONE
OLDFILEUID:NONE
NEWFILEUID:NONE

<OFX>
<BANKMSGSRSV1>
<STMTTRNRS>
<TRNUID>1001
<STATUS><CODE>0<SEVERITY>INFO</STATUS>
<STMTRS>
<CURDEF>EUR
<BANKACCTFROM><BANKID>12345<ACCTID>00001234567<ACCTTYPE>CHECKING</BANKACCTFROM>
<BANKTRANLIST>
<DTSTART>20260101
<DTEND>20260131
<STMTTRN>
<TRNTYPE>DEBIT
<DTPOSTED>20260115
<TRNAMT>-50.50
<FITID>UNIQUE_BANK_ID_XYZ
<NAME>Test payee
</STMTTRN>
</BANKTRANLIST>
</STMTRS>
</STMTTRNRS>
</BANKMSGSRSV1>
</OFX>
"""
    importer = OfxImporter()
    txns = importer.parse(io.BytesIO(ofx_content.encode("ascii")))
    assert txns[0].reference == "UNIQUE_BANK_ID_XYZ"
    # Hash should be based on FITID, so it's stable across re-imports
    expected_hash = hashlib.sha256(b"UNIQUE_BANK_ID_XYZ").hexdigest()
    assert txns[0].import_hash == expected_hash


# ── Import service tests ─────────────────────────────────────────


async def test_import_service_detects_duplicates(db_session):
    from budgie.importers.base import ImportedTransaction
    from budgie.models.account import Account
    from budgie.models.user import User
    from budgie.services.importer import confirm_import

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    account = Account(
        user_id=user.id, name="Checking", account_type="checking", on_budget=True
    )
    db_session.add(account)
    await db_session.commit()

    txns = [
        ImportedTransaction(
            date=datetime.date(2026, 1, 15),
            amount=-5050,
            description="Carrefour",
            reference="TXN001",
        )
    ]

    # First import — should succeed
    result1 = await confirm_import(db_session, account.id, txns)
    assert result1.imported == 1
    assert result1.duplicates == 0

    # Second import — same hash → duplicate
    result2 = await confirm_import(db_session, account.id, txns)
    assert result2.imported == 0
    assert result2.duplicates == 1


async def test_import_service_partial_duplicates(db_session):
    from budgie.importers.base import ImportedTransaction
    from budgie.models.account import Account
    from budgie.models.user import User
    from budgie.services.importer import confirm_import

    user = User(username="alice", hashed_password="hash")
    db_session.add(user)
    await db_session.commit()

    account = Account(
        user_id=user.id, name="Checking", account_type="checking", on_budget=True
    )
    db_session.add(account)
    await db_session.commit()

    txn_existing = ImportedTransaction(
        date=datetime.date(2026, 1, 15),
        amount=-5050,
        description="Carrefour",
        reference="TXN001",
    )
    txn_new = ImportedTransaction(
        date=datetime.date(2026, 1, 16),
        amount=-12000,
        description="EDF",
        reference="TXN002",
    )

    await confirm_import(db_session, account.id, [txn_existing])
    result = await confirm_import(db_session, account.id, [txn_existing, txn_new])
    assert result.imported == 1
    assert result.duplicates == 1


# ── French decimal / BudgetBanque format ────────────────────────


def test_csv_importer_french_decimal():
    """CSV with French decimal separator (comma) and space thousands separator."""
    from budgie.importers.csv_importer import CsvImporter

    csv_content = (
        "dateOp;label;amount\n"
        "2026-01-15;Carte Carrefour;-50,50\n"
        '2026-01-16;Salaire;"3 829,82"\n'
    )
    importer = CsvImporter()
    txns = importer.parse(
        io.BytesIO(csv_content.encode()),
        column_map={"date": "dateOp", "description": "label", "amount": "amount"},
        date_format="%Y-%m-%d",
        separator=";",
        decimal=",",
        thousands=" ",
    )
    assert len(txns) == 2
    assert txns[0].amount == -5050
    assert txns[1].amount == 382982


# ── Real-file integration tests (skipped if files absent) ───────
_SENSITIVE = pathlib.Path("sensitive-test-data")


def test_bb_csv_real_file():
    """Integration test against the real BudgetBanque CSV export."""
    from budgie.importers.csv_importer import CsvImporter

    csv_path = next(_SENSITIVE.glob("*.csv"), None) if _SENSITIVE.exists() else None
    if csv_path is None:
        pytest.skip("No real CSV bank export found in sensitive-test-data/")

    importer = CsvImporter()
    with open(csv_path, "rb") as f:
        txns = importer.parse(
            f,
            column_map={
                "date": "dateOp",
                "description": "label",
                "payee": "supplierFound",
                "amount": "amount",
            },
            separator=";",
            decimal=",",
            thousands=" ",
            date_format="%Y-%m-%d",
        )
    assert len(txns) > 0
    # First row: Tesla -7.99€ → -799 centimes
    assert txns[0].amount == -799
    assert txns[0].date == datetime.date(2026, 2, 27)
    assert txns[0].payee_name is not None
    assert "tesla" in txns[0].payee_name.lower()


def test_bb_excel_real_file():
    """Integration test against the real BudgetBanque Excel export."""
    from budgie.importers.excel_importer import ExcelImporter

    xlsx_path = next(_SENSITIVE.glob("*.xlsx"), None) if _SENSITIVE.exists() else None
    if xlsx_path is None:
        pytest.skip("No real Excel bank export found in sensitive-test-data/")

    importer = ExcelImporter()
    with open(xlsx_path, "rb") as f:
        txns = importer.parse(
            f,
            column_map={"date": 0, "description": 2, "payee": 5, "amount": 6},
            header=None,
        )
    assert len(txns) > 0
    # First row: Tesla -7.99€ → -799 centimes
    assert txns[0].amount == -799
    assert txns[0].date == datetime.date(2026, 2, 27)
    assert txns[0].payee_name == "tesla inc"
