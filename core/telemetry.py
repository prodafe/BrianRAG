import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from config import Config

logger = logging.getLogger(__name__)


def setup_telemetry(app=None):
    """初始化 OpenTelemetry，兼容不同版本的 OTLP 导出器"""
    if not Config.ENABLE_TELEMETRY:
        logger.info("Telemetry disabled")
        return

    try:
        # 设置 Tracer Provider
        provider = TracerProvider()

        # 兼容新版 OTLP 导出器（不再使用 insecure 参数）
        # 如果配置了 OTLP_ENDPOINT，则创建导出器
        if hasattr(Config, "OTLP_ENDPOINT") and Config.OTLP_ENDPOINT:
            # 新版 SDK 使用 ssl_channel_credentials 参数，None 表示非加密连接
            try:
                otlp_exporter = OTLPSpanExporter(endpoint=Config.OTLP_ENDPOINT)
            except TypeError:
                # 旧版 fallback: 尝试 insecure=True
                otlp_exporter = OTLPSpanExporter(endpoint=Config.OTLP_ENDPOINT, insecure=True)

            processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(processor)
            logger.info(f"OTLP 导出器已配置，端点: {Config.OTLP_ENDPOINT}")
        else:
            logger.info("未配置 OTLP_ENDPOINT，将只生成 trace 但不导出")

        trace.set_tracer_provider(provider)

        # 自动仪表化
        if app:
            FastAPIInstrumentor.instrument_app(app)
        RequestsInstrumentor().instrument()

        # 如果有 SQLAlchemy 引擎（例如在 app 对象中或全局），可以按需添加
        # if hasattr(app, 'db_engine'):
        #     SQLAlchemyInstrumentor().instrument(engine=app.db_engine)

        logger.info("OpenTelemetry 已启动")
    except Exception as e:
        logger.error(f"OpenTelemetry 初始化失败: {e}，将跳过追踪功能")
        # 不抛出异常，保证应用继续运行
