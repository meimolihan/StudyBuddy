package web

import "testing"

func TestRandomSplashVerse(t *testing.T) {
	if len(splashVerses) < 40 {
		t.Fatalf("诗句池过小: %d", len(splashVerses))
	}
	seen := map[string]bool{}
	distinct := 0
	for i := 0; i < 30; i++ {
		v := RandomSplashVerse()
		if v.L1 == "" || v.L2 == "" || v.Author == "" {
			t.Fatalf("诗句字段为空: %+v", v)
		}
		key := v.L1 + v.L2
		if !seen[key] {
			seen[key] = true
			distinct++
		}
	}
	if distinct < 5 {
		t.Fatalf("30 次抽样仅 %d 句不同，随机性异常", distinct)
	}
	t.Logf("诗句池 %d 句，30 次抽样命中 %d 句不同，随机性正常", len(splashVerses), distinct)
}
