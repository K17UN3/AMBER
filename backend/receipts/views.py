from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import OCRJob
from .serializers import OCRJobSerializer

MAX_IMAGE_SIZE = 10 * 1024 * 1024


class ReceiptAnalyzeView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        image = request.FILES.get("image")
        if image is None:
            return Response(
                {"detail": "レシート画像を選択してください。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not image.content_type or not image.content_type.startswith("image/"):
            return Response(
                {"detail": "画像ファイルを選択してください。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if image.size > MAX_IMAGE_SIZE:
            return Response(
                {"detail": "画像サイズは10MB以下にしてください。"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = OCRJob.objects.create(
            user=request.user,
            image=image,
            original_filename=image.name,
            content_type=image.content_type,
            file_size=image.size,
        )
        return Response(OCRJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class OCRJobDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, job_id):
        job = OCRJob.objects.filter(pk=job_id, user=request.user).first()
        if job is None:
            return Response({"detail": "OCRジョブが見つかりません。"}, status=status.HTTP_404_NOT_FOUND)
        return Response(OCRJobSerializer(job).data)
