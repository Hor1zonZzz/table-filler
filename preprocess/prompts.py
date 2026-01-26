"""Classification prompt templates for PDF pre-classification.

This module defines the prompts used by the VL model to classify PDFs
into supplier contracts vs. other documents.
"""

CLASSIFY_PROMPT = """请分析这份PDF文档，判断是否为符合条件的供应商合同。

## 分类标准

1. **是否为甲乙双方合同**：
   - 必须是单个甲乙双方签订的合同
   - 不能是三方或多方合同
   - 不能是发票、报告、通知等非合同文档

2. **甲方名称是否包含"昇腾"**：
   - 甲方名称中需要含有"昇腾"二字
   - 例如："北京昇腾科技有限公司"、"昇腾创新人工智能有限公司"等昇腾相关企业

3. **乙方是否为供应商**：
   - 乙方应为提供服务、硬件、软件、咨询、维护等的供应商
   - 乙方向甲方提供商品或服务

## 输出格式

请以JSON格式输出分析结果，必须包含以下字段：

```json
{
  "is_two_party_contract": true或false,
  "party_a": "甲方名称（如有）",
  "party_a_contains_shengteng": true或false,
  "party_b": "乙方名称（如有）",
  "party_b_is_supplier": true或false,
  "party_b_provides": "乙方提供的服务/商品类型（如有）",
  "reason": "简要说明分类理由"
}
```

## 注意事项

- 仔细阅读文档首页和签章页
- 如果无法确定某项信息，请如实填写无法确定
- party_a 和 party_b 如果不适用请填 null
- party_b_provides 如果不是供应商合同请填 null

请只返回JSON，不要包含其他文字。
"""
