# 写测试

## 步骤

1. 读被测代码和已有测试，沿用仓库现有的测试风格和目录。
2. **先列测试点，再写代码**。按三类列出：
   - 正常：典型输入。
   - 边界：空、单元素、最大最小值、刚好在阈值上。
   - 异常：非法输入、错误返回、超时（涉及时）。
3. 把测试点写成表驱动测试，每个用例一个能看懂的名字。
4. 运行测试，确认通过；修 bug 时先确认新测试在修复前失败。
5. 报告：列出测试点、测试文件位置、运行命令和结果。

## Go

- 用标准库 `testing`，表驱动 + `t.Run`；不引入断言库，除非仓库已经在用。
- 测试文件与被测文件同目录，命名 `xxx_test.go`。
- 失败信息写清输入、期望、实际：`t.Errorf("f(%v) = %v, want %v", in, got, want)`。
- 需要时加 `t.Parallel()`；用 `t.TempDir()` 处理临时文件。

```go
func TestTwoSum(t *testing.T) {
	tests := []struct {
		name   string
		nums   []int
		target int
		want   []int
	}{
		{"基本", []int{2, 7, 11, 15}, 9, []int{0, 1}},
		{"负数", []int{-3, 4, 3, 90}, 0, []int{0, 2}},
		{"重复元素", []int{3, 3}, 6, []int{0, 1}},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := twoSum(tt.nums, tt.target)
			if !slices.Equal(got, tt.want) {
				t.Errorf("twoSum(%v, %d) = %v, want %v", tt.nums, tt.target, got, tt.want)
			}
		})
	}
}
```

## Python

- 用 pytest，`@pytest.mark.parametrize` 做表驱动，`ids=` 给用例命名。
- 异常用 `pytest.raises`；临时文件用 `tmp_path` fixture。

## 输出格式

```
## 测试点
| 类别 | 用例 | 输入 | 期望 |

## 改动
- path/to/xxx_test.go：新增 N 个用例

## 运行结果
go test ./... 的实际输出（通过/失败）
```
