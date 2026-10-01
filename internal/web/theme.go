package web

// 主题（皮肤）系统。
//
// 设计要点：
//   - 主题只通过 <html data-skin="..."> 属性驱动，全部样式由 CSS 变量承载，
//     不触碰任何业务逻辑与 DOM 结构。
//   - 注册时按性别给出默认主题（男→boy / 女→girl）；学生在 UI 里改过之后，
//     以自己选的主题为准（users.skin），不再随性别变化。
//   - users.skin 为空串表示「从未手动选择过」，此时按性别实时推导，
//     这样后台建号（未填性别）等历史数据也能拿到合理默认值。

// GenderMale / GenderFemale 数据库里保存的性别取值。
const (
	GenderMale   = "male"
	GenderFemale = "female"
)

// SkinDefault 默认主题键（= 原始蓝色主题，不产生任何覆盖）。
const SkinDefault = "default"

// Skin 一个可选主题的元信息，用于渲染主题选择器。
type Skin struct {
	Key   string // 写入 data-skin 与数据库的值
	Name  string // 中文名
	Emoji string
	Desc  string
	C1    string // 色卡主色
	C2    string // 色卡副色
	For   string // 推荐性别："" / male / female（仅用于标记推荐，不限制选择）
}

// Skins 全部可选主题。顺序即选择器中的展示顺序。
var Skins = []Skin{
	{Key: SkinDefault, Name: "清新蓝", Emoji: "💙", Desc: "清爽耐看，默认主题", C1: "#2f6fd0", C2: "#7b5cd6"},
	{Key: "boy", Name: "男生主题", Emoji: "🚀", Desc: "深海蓝 · 科技感", C1: "#2563eb", C2: "#0ea5e9", For: GenderMale},
	{Key: "girl", Name: "女生主题", Emoji: "🌸", Desc: "樱花粉 · 甜美范", C1: "#e0518f", C2: "#a855f7", For: GenderFemale},
	{Key: "forest", Name: "森林绿", Emoji: "🌿", Desc: "护眼绿 · 自然风", C1: "#2f9e6b", C2: "#7cc27a"},
	{Key: "sunset", Name: "暖阳橙", Emoji: "🌅", Desc: "温暖橙 · 有活力", C1: "#ea7a2a", C2: "#e0553f"},
	{Key: "starry", Name: "星空紫", Emoji: "🌌", Desc: "梦幻紫 · 想象力", C1: "#7c4ddb", C2: "#3f7fe0"},
}

// SkinValid 判断主题键是否受支持。
func SkinValid(key string) bool {
	for _, s := range Skins {
		if s.Key == key {
			return true
		}
	}
	return false
}

// SkinForGender 返回性别对应的默认主题。
func SkinForGender(gender string) string {
	switch gender {
	case GenderMale:
		return "boy"
	case GenderFemale:
		return "girl"
	default:
		return SkinDefault
	}
}

// ResolveSkin 计算某用户实际生效的主题：手动选过就用选的，否则按性别匹配。
func ResolveSkin(saved, gender string) string {
	if SkinValid(saved) {
		return saved
	}
	return SkinForGender(gender)
}

// GenderCN 性别中文名（用于界面展示）。
func GenderCN(gender string) string {
	switch gender {
	case GenderMale:
		return "男生"
	case GenderFemale:
		return "女生"
	default:
		return "未设置"
	}
}

// skinName 主题键 → 中文名；未知键回落到默认主题名。
func skinName(key string) string {
	for _, s := range Skins {
		if s.Key == key {
			return s.Name
		}
	}
	return Skins[0].Name
}
