// Package docx 用标准库 archive/zip 直接生成 Office Open XML（.docx）试卷。
//
// 特点：
//   - 零第三方依赖，纯 Go 实现；
//   - 选项前为 **Word 原生可交互复选框**（w14:checkbox SDT 控件），在 Word/WPS 中单击即可勾选；
//   - 自动预填学生姓名、班级、当前日期，并附参考答案便于核对得分。
package docx

import (
	"archive/zip"
	"fmt"
	"io"
	"strings"
	"time"
)

// Q 试卷中的一道题。
type Q struct {
	No      int      // 题号，从 1 开始
	Type    string   // "单选" / "多选"
	Stem    string   // 题干
	Options []string // 选项文本
	Answers []string // 正确答案文本（用于文末答案）
}

// Exam 一份待导出的试卷。
type Exam struct {
	Title    string // 试卷标题
	Student  string // 学生姓名
	Class    string // 班级
	Date     string // 日期（为空则取当天）
	Lesson   string // 单元 · 课
	BankSize int    // 题库题数
	Tip      string // 顶部提示（可为空）
	Questions []Q
}

// Build 生成 docx 并写入 w。
func Build(w io.Writer, e Exam) error {
	if e.Date == "" {
		e.Date = time.Now().Format("2006年01月02日")
	}
	zw := zip.NewWriter(w)
	defer zw.Close()

	now := time.Now().Format(time.RFC3339)
	files := []struct{ name, data string }{
		{"[Content_Types].xml", contentTypes},
		{"_rels/.rels", rootRels},
		{"word/_rels/document.xml.rels", docRels},
		{"word/styles.xml", styles},
		{"docProps/core.xml", fmt.Sprintf(coreTpl, xmlEsc(e.Title), now, now)},
		{"docProps/app.xml", appXML},
		{"word/document.xml", document(e)},
	}
	for _, f := range files {
		fw, err := zw.Create(f.name)
		if err != nil {
			return err
		}
		if _, err := strings.NewReader(f.data).WriteTo(fw); err != nil {
			return err
		}
	}
	return nil
}

func document(e Exam) string {
	var b strings.Builder
	b.WriteString(xmlDecl)
	b.WriteString(`<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"><w:body>`)

	// 标题
	b.WriteString(para(0, run(true, 36, e.Title)))
	sub := e.Lesson
	if e.BankSize > 0 {
		sub += fmt.Sprintf("  （本题库共 %d 题，本次 10 题）", e.BankSize)
	}
	b.WriteString(para(120, run(false, 20, sub)))

	// 信息栏：姓名 / 班级 / 日期 / 得分
	info := fmt.Sprintf("姓名：%s　　班级：%s　　日期：%s　　得分：__________",
		orDefault(e.Student, "________"), orDefault(e.Class, "________"), e.Date)
	b.WriteString(para(160, run(false, 22, info)))

	if strings.TrimSpace(e.Tip) != "" {
		b.WriteString(para(120, run(false, 20, e.Tip)))
	}
	b.WriteString(para(120, run(false, 20, "说明：每题 10 分，满分 100 分。请点击选项前的方框作答，单选选 1 个，多选可选多个。")))

	// 题目
	id := 1000
	for _, q := range e.Questions {
		stem := fmt.Sprintf("%d. （%s）%s", q.No, q.Type, q.Stem)
		b.WriteString(para(200, run(false, 22, stem)))
		for i, opt := range q.Options {
			letter := string(rune('A' + i))
			p := `<w:p><w:pPr><w:spacing w:before="60" w:after="60"/><w:ind w:left="480"/></w:pPr>`
			p += checkbox(&id)
			p += run(false, 22, fmt.Sprintf(" %s. %s", letter, opt))
			p += `</w:p>`
			b.WriteString(p)
		}
	}

	// 参考答案
	b.WriteString(para(320, run(true, 26, "参考答案")))
	for _, q := range e.Questions {
		line := fmt.Sprintf("%d. %s", q.No, strings.Join(q.Answers, "、"))
		b.WriteString(para(60, run(false, 20, line)))
	}

	b.WriteString(`<w:sectPr><w:pgSz w:w="11906" w:h="16838"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="851" w:footer="992" w:gutter="0"/></w:sectPr>`)
	b.WriteString(`</w:body></w:document>`)
	return b.String()
}

// checkbox 返回一个 Word 原生复选框控件（未勾选状态）。
func checkbox(id *int) string {
	*id++
	return fmt.Sprintf(
		`<w:sdt><w:sdtPr><w:id w:val="%d"/>`+
			`<w14:checkbox><w14:checked w14:val="0"/>`+
			`<w14:checkedState w14:val="2612" w14:font="MS Gothic"/>`+
			`<w14:uncheckedState w14:val="2610" w14:font="MS Gothic"/></w14:checkbox>`+
			`<w:text/></w:sdtPr><w:sdtContent><w:r><w:rPr>`+
			`<w:rFonts w:ascii="MS Gothic" w:hAnsi="MS Gothic" w:eastAsia="MS Gothic"/>`+
			`<w:sz w:val="32"/></w:rPr><w:t>&#9744;</w:t></w:r></w:sdtContent></w:sdt>`, *id)
}

func para(before int, inner ...string) string {
	b := strings.Builder{}
	b.WriteString(fmt.Sprintf(`<w:p><w:pPr><w:spacing w:before="%d" w:after="%d"/></w:pPr>`, before, before/2))
	for _, s := range inner {
		b.WriteString(s)
	}
	b.WriteString(`</w:p>`)
	return b.String()
}

// run 生成一段文字；bold 加粗，size 为半磅值（22 ≈ 11pt）。
func run(bold bool, size int, text string) string {
	b := strings.Builder{}
	b.WriteString(`<w:r><w:rPr>`)
	if bold {
		b.WriteString(`<w:b/>`)
	}
	b.WriteString(fmt.Sprintf(`<w:sz w:val="%d"/><w:szCs w:val="%d"/></w:rPr>`, size, size))
	b.WriteString(fmt.Sprintf(`<w:t xml:space="preserve">%s</w:t></w:r>`, xmlEsc(text)))
	return b.String()
}

func xmlEsc(s string) string {
	s = strings.ReplaceAll(s, "&", "&amp;")
	s = strings.ReplaceAll(s, "<", "&lt;")
	s = strings.ReplaceAll(s, ">", "&gt;")
	s = strings.ReplaceAll(s, `"`, "&quot;")
	s = strings.ReplaceAll(s, "'", "&apos;")
	return s
}

func orDefault(s, d string) string {
	if strings.TrimSpace(s) == "" {
		return d
	}
	return s
}

const xmlDecl = `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`

const contentTypes = xmlDecl + `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">` +
	`<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>` +
	`<Default Extension="xml" ContentType="application/xml"/>` +
	`<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>` +
	`<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>` +
	`<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>` +
	`<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>` +
	`</Types>`

const rootRels = xmlDecl + `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
	`<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>` +
	`<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>` +
	`<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>` +
	`</Relationships>`

const docRels = xmlDecl + `<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">` +
	`<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>` +
	`</Relationships>`

const styles = xmlDecl + `<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">` +
	`<w:docDefaults><w:rPrDefault><w:rPr>` +
	`<w:rFonts w:ascii="宋体" w:hAnsi="宋体" w:eastAsia="宋体"/><w:sz w:val="22"/></w:rPr></w:rPrDefault>` +
	`<w:pPrDefault><w:pPr><w:spacing w:line="360" w:lineRule="auto"/></w:pPr></w:pPrDefault>` +
	`</w:docDefaults></w:styles>`

const coreTpl = xmlDecl + `<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">` +
	`<dc:title>%s</dc:title><dc:creator>StudyBuddy</dc:creator><cp:lastModifiedBy>StudyBuddy</cp:lastModifiedBy>` +
	`<dcterms:created xsi:type="dcterms:W3CDTF">%s</dcterms:created>` +
	`<dcterms:modified xsi:type="dcterms:W3CDTF">%s</dcterms:modified>` +
	`</cp:coreProperties>`

const appXML = xmlDecl + `<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">` +
	`<Application>StudyBuddy</Application></Properties>`
