import csv
import io

from rest_framework import generics, status
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.reconciliation.loaders import parse_order_row

from .models import Order
from .serializers import OrderSerializer


class OrderListView(generics.ListAPIView):
    """GET /api/orders/ - the current user's orders, most recent upload first."""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(owner=self.request.user).order_by("-uploaded_at", "order_id")


class OrderUploadView(APIView):
    """POST /api/orders/upload/ (multipart, field name 'file') - replaces the
    current user's order dataset with the rows in the uploaded CSV.

    Re-uploading is a full replace (not an append) so reconciliation stays
    deterministic and repeatable for a given file, rather than accumulating
    duplicate rows across repeated uploads during testing.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    REQUIRED_COLUMNS = {"order_id", "currency", "gross_amount", "discount", "net_amount", "status"}

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
        for i, raw_row in enumerate(reader, start=2):  # header is line 1
            try:
                parsed = parse_order_row(raw_row)
                rows_to_create.append(
                    Order(
                        owner=request.user,
                        order_id=parsed.order_id,
                        order_id_normalized=parsed.norm_id,
                        order_date_raw=parsed.order_date,
                        customer_email=parsed.customer_email,
                        currency=parsed.currency,
                        gross_amount=parsed.gross_amount,
                        discount=parsed.discount,
                        net_amount=parsed.net_amount,
                        status=parsed.status,
                    )
                )
            except (KeyError, TypeError) as exc:
                skipped_rows.append(f"row {i}: {exc}")

        Order.objects.filter(owner=request.user).delete()
        Order.objects.bulk_create(rows_to_create)

        return Response(
            {"created": len(rows_to_create), "skipped_rows": skipped_rows},
            status=status.HTTP_201_CREATED,
        )
