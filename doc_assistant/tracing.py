from phoenix.otel import register

# 配置 Phoenix 追踪器
tracer_provider = register(
    project_name="ltc-doc-assistant",  # 默认是 'default'
    auto_instrument=True,              # 基于已安装的 OI 依赖项自动仪表化你的应用
    endpoint="http://localhost:6006/v1/traces",
)
