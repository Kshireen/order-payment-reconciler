import csv
import io

from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reconciliation.loaders import parse_payment_row

from .models import Payment
from .serializers import PaymentSerializer


class PaymentListView(generics.ListAPIView):
    """GET /api/payments/ - the current user's payments, most recent upload first."""

    serializer_class = PaymentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Payment.objects.filter(owner=self.request.user).order_by("-uploaded_at", "transaction_ref")


class PaymentUploadView(APIView):
    """POST /api/payments/upload/ (multipart, field name 'file') - replaces the
    current user's payment dataset with the rows in the uploaded CSV. Same
    full-replace semantics as OrderUploadView, for the same reason."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    REQUIRED_COLUMNS = {"transaction_ref", "order_reference", "currency", "amount", "type", "status"}

    def post(self, request):
        upload = request.FILES.get("file")
        if not upload:
            return Response({"detail": "No file provided (expected multipart field 'file')."}, status=400)

        try:
            decoded = upload.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            return Response({"detail": "File is not valid UTF-8 text."}, status=400)

        reader = csv.DictReader(io.StringIO(decoded))
        if reader.fieldnames is None or not self.REQUIRED_COLUMNS.issubset(set(reader.fieldnames)):
            missing = self.REQUIRED_COLUMNS - set(reader.fieldnames or [])
            return Response({"detail": f"CSV missing required columns: {sorted(missing)}"}, status=400)

        rows_to_create = []
        skipped_rows = []
        for i, raw_row in enumerate(reader, start=2):
            try:
                parsed = parse_payment_row(raw_row)
                rows_to_create.append(
                    Payment(
                        owner=request.user,
                        transaction_ref=parsed.transaction_ref,
                        processed_at_raw=parsed.processed_at,
                        order_reference=parsed.order_reference,
                        order_reference_normalized=parsed.norm_ref,
                        currency=parsed.currency,
                        amount=parsed.amount,
                        fee=parsed.fee,
                        net_settled=parsed.net_settled,
                        type=parsed.type,
                        status=parsed.status,
                    )
                )
            except (KeyError, TypeError) as exc:
                skipped_rows.append(f"row {i}: {exc}")

        Payment.objects.filter(owner=request.user).delete()
        Payment.objects.bulk_create(rows_to_create)

        return Response(
            {"created": len(rows_to_create), "skipped_rows": skipped_rows},
            status=status.HTTP_201_CREATED,
        )
