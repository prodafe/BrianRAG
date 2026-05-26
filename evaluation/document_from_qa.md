## 1. 什么是 BrianRAG？

BrianRAG 是一个基于检索增强生成的企业知识库问答系统，支持多格式文档、混合检索、知识图谱和多模态理解。

## 2. BrianRAG 支持哪些文档格式？

支持 txt, pdf, md, docx, html, csv, jpg, jpeg, png, gif, bmp 等格式。

## 3. 如何上传文档到 BrianRAG？

在 WebUI 侧边栏「文档管理」区域，点击文件上传按钮，选择本地文档，可多选，然后点击「构建索引」即可。

## 4. BrianRAG 的检索模式有哪些？

有快速模式 (RAG)、智能体模式 (Agentic)、图谱工作流 (LangGraph) 和多模态智能体四种。

## 5. 如何切换问答模式？

在 WebUI 侧边栏的「配置」区域，使用「问答模式」单选按钮进行切换。

## 6. 什么是混合检索？

混合检索结合了 BM25 关键词检索和 FAISS 向量检索，通过 alpha 参数平衡两者权重，提升召回率和精度。

## 7. 如何调整检索参数？

在侧边栏配置中可以调节 Top-K（检索片段数）、关键词权重 (Alpha) 和相似度阈值。

## 8. BrianRAG 是否支持增量索引？

支持。勾选「增量添加新文档」后，只会对新上传的文件建立索引，避免全量重建。

## 9. 如何删除已索引的文档？

在侧边栏「已索引文档」列表中，点击文档旁边的垃圾桶图标即可删除，删除后需全量重建以清除残留数据。

## 10. 什么是知识图谱增强检索？

从文档中提取实体关系构建图，在检索时根据问题实体查询关联节点，返回相关文本块，实现跨文档推理。

## 11. BrianRAG 使用的是什么嵌入模型？

使用 bge-m3:latest 作为嵌入模型，通过 Ollama 调用，维度为 1024。

## 12. 如何修改嵌入模型？

在 config.py 中修改 EMBEDDING_MODEL 和 EMBEDDING_DIM 配置，然后全量重建索引。

## 13. BrianRAG 支持哪些 LLM 模型？

支持通过 Ollama 拉取的所有模型，例如 qwen2.5:7b, mistral-nemo:latest, llama3.2:3b 等。

## 14. 如何更换 LLM 模型？

在 config.py 中修改 LLM_MODEL 参数，然后重启服务。

## 15. BrianRAG 的自我修正功能是什么？

启用后，系统会评估生成答案的质量，若得分低于阈值则改写查询并重新检索生成，最多重试多次。

## 16. 如何启用自我修正？

在 config.py 中设置 ENABLE_SELF_CORRECTION = True，并配置相关参数。

## 17. BrianRAG 是否支持图片描述生成？

支持。通过视觉模型（如 qwen2.5-vl:7b）为图片生成中文描述，并将描述纳入文本检索。

## 18. 如何配置视觉模型？

在 document_loader.py 的 generate_image_caption 函数中修改模型名称，并确保已通过 ollama pull 下载。

## 19. BrianRAG 的 Reranker 有什么作用？

重排序模型（如 bge-reranker-v2-m3）对混合检索返回的候选片段进行精细打分，提升最终答案质量。

## 20. 如何开启 Reranker？

在 config.py 中设置 ENABLE_RERANK = True，并指定 RERANK_MODEL 路径。

## 21. BrianRAG 是否支持多轮对话？

支持。系统会保留最近 MAX_HISTORY_TURNS 轮的对话历史，作为上下文传递给 LLM。

## 22. 如何清空对话历史？

在侧边栏点击「清空对话历史」按钮即可。

## 23. BrianRAG 的异步索引是什么？

构建索引在后台线程中执行，前端不阻塞，用户可同时进行问答，进度条实时更新。

## 24. 如何反馈答案质量？

每条答案下方有「有用」「无用」按钮，点击后可填写评语，反馈会记录到 feedback.jsonl 文件中。

## 25. BrianRAG 是否支持参数自动调优？

支持。在侧边栏点击「参数自动调优 (基于反馈)」，系统会利用负面反馈数据搜索最优的 top_k, alpha, score_threshold 组合。

## 26. 如何导出知识图谱可视化？

在「知识图谱」标签页中点击「生成并预览图谱」，可下载 HTML 文件，用浏览器打开交互式查看。

## 27. BrianRAG 是否支持图谱多跳推理？

支持。在 config.py 中设置 GRAPH_HOPS 参数（默认 1），检索时会向外探索邻居实体，增强跨文档关联能力。

## 28. 如何启用实体规范化？

在 config.py 中设置 ENABLE_ENTITY_NORMALIZATION = True，并配置 Splink 规则，系统会自动合并相似实体。

## 29. BrianRAG 支持多模态问答吗？

支持。通过多模态智能体模式，可以同时处理文本、图片、表格和图表，自动路由到对应处理节点。

## 30. 如何评估 BrianRAG 的检索质量？

使用 evaluation/evaluate.py 脚本，基于 RAGAS 框架计算忠实度、答案相关性、上下文相关性等指标。

## 31. BrianRAG 的日志保存在哪里？

日志文件位于项目根目录下的 logs/ 文件夹中，默认为 tinyrag.log。

## 32. 如何修改日志级别？

在 config.py 中调整 LOG_LEVEL 变量，如设为 INFO, DEBUG, WARNING 等。

## 33. BrianRAG 是否支持 API 调用？

目前未提供独立 API，但可通过扩展 FastAPI 封装 RAGPipeline 实现。

## 34. BrianRAG 的默认索引目录是什么？

默认为项目根目录下的 index/ 文件夹，包含 FAISS 索引、BM25 序列化、图谱文件等。

## 35. 如何迁移模型文件到其他盘？

设置环境变量 OLLAMA_MODELS 指向新目录，然后将 ~/.ollama/models 下的文件剪切过去，重启 Ollama。

## 36. BrianRAG 是否支持联网搜索？

不支持，所有处理均在本地完成，保证数据隐私。

## 37. 如何处理上传的扫描 PDF？

系统会提取其中的图片，并通过视觉模型生成描述；文本部分需要 OCR，目前需要额外集成 OCR 工具。

## 38. BrianRAG 的配置文件在哪？

主配置为 config.py，位于项目根目录。

## 39. 如何升级 BrianRAG？

备份 config.py 和 index/ 目录，然后拉取最新代码，重新安装依赖，重启服务。

## 40. BrianRAG 的开源协议是什么？

本项目为自研企业级系统，非开源；但使用了 Apache 2.0 和 MIT 协议的第三方组件。

