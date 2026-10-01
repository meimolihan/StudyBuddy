# 教材内容目录规范

StudyBuddy 在启动时自动扫描 `content/` 目录树生成课程导航。
**新增年级 / 册别 / 科目 / 课程，只需按本规范放入 HTML 文件，无需改任何代码。**

## 一、标准结构

```
content/<stage>/<publisher>/grade<N>/volume<N>/<subject>/<NN-单元名>/<NN-课名>.html

content/primary/pep/grade4/volume1/chinese/01-自然之美/01-观潮.html
                                                    02-走月亮.html
                                            02-提问/05-一个豆荚里的五粒豆.html
                                    math/01-大数的认识/01-亿以内数的认识.html
```

| 层级 | 取值 | 说明 |
|------|------|------|
| `<stage>` | `primary` / `middle` / `high` | 学段：小学 / 初中 / 高中 |
| `<publisher>` | `pep` 等 | 出版社（人教社 = pep） |
| `grade<N>` | `grade1` ~ `grade12` | 年级 |
| `volume<N>` | `volume1` / `volume2` | 册别：上册 / 下册 |
| `<subject>` | `chinese` / `math` / `english` / `morallaw` / `science` | 科目 |
| `<NN-单元名>` | 如 `01-自然之美` | 单元目录，**两位序号**保证排序；可省略 |
| `<NN-课名>.html` | 如 `01-观潮.html` | 课程文件，**两位序号**保证排序 |

要点：

- **路径即元数据**：年级、册别、科目都由目录名表达，文件名只写「序号 + 课名」，不再重复年级册别。
- **两位序号**：`01` `02` … `11`，保证文件管理器与扫描结果顺序一致。
- **单元目录可省略**：课程文件直接放在科目目录下时，归入「未分单元」。
- **不合规路径自动忽略**：中文命名的占位目录（如 `五年级上册/数学/`）不会被识别，也不会报错。

## 一·二、高考复习专题（review 目录）

高考复习专题不属于任何教材册别，用 `review` 段顶替 `volume<N>` 层，
导航中展示为独立册别「**高考复习**」（排在该年级上/下册之后）：

```
content/<stage>/<publisher>/grade<N>/review/<subject>/<NN-专题名>.html

content/high/pep/grade3/review/math/01-函数与导数.html
content/high/pep/grade3/review/biology/01-分子与细胞.html
```

- `review` 直接放在 `grade<N>` 下，**不带 volume 层**；其下的 `<subject>` 必须是标准科目目录名。
- 专题文件同样是「两位序号 + 专题名」，可再套一层专题组目录（同单元规则）。
- 层级仍为 学段 → 出版社 → 年级 → 高考复习 → 科目 → 专题。

## 二、课程 HTML 的要求

系统从课程 HTML 中读取内置的题库数组：

```js
const ALL = [
  {t:"s",q:"题干……",o:["选项A","选项B","选项C","选项D"],a:["A"]},
  {t:"m",q:"题干……",o:["选项A","选项B","选项C","选项D"],a:["A","B"]}
];
```

- `t`：`s` 单选 / `m` 多选
- `o`：四个选项文本（顺序即 A/B/C/D）
- `a`：正确答案字母

解析器按**引号边界**逐字符读取，选项内可含逗号（如英语 `Yes, I do.`）与转义引号。

## 三、批量导入与规范化

旧命名的文件（如 `四年级语文上册 · 第一单元 自然之美 · 第1课 观潮.html`）
可用项目内置工具一键整理成标准结构：

```bash
python scripts/migrate_content.py --dry-run   # 预览
python scripts/migrate_content.py             # 执行
```

该工具会：解析旧文件名中的单元 / 课序号 → 建立标准目录 → 移动文件 → 清理遗留空目录。

> 扫描器同时保留对旧命名的兼容解析，即便不迁移也能识别（见 `internal/textbook/parseLessonLegacy`）。

## 四、自检

```bash
go run ./tools/smoke    # 扫描课程数、题库题数、出题、判分、docx
```

启动时控制台会打印「识别课程 N 门」，可据此确认新放的教材是否被正确识别。
