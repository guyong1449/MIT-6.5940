# MIT 6.5940 Lab5 学习笔记

## 实验目标
实现量化矩阵乘法的优化：INT8 激活 × INT4 权重

---

## 一、C++ 语法基础

### 1.1 结构体和指针

```cpp
// 结构体定义
struct matmul_params {
    matrix A, B, C;
    int block_size;
    float* scales;
    float* offset;
};

// 访问成员
matmul_params params;      // 值类型
params.block_size = 32;    // 使用 .

matmul_params* params_ptr; // 指针类型
params_ptr->block_size = 32; // 使用 ->
// 等价于 (*params_ptr).block_size = 32;
```

**记忆方法：**
- `.` → 点接触，直接访问
- `->` → 箭头指向，通过指针访问

### 1.2 位运算符

| 运算符 | 含义 | 例子 |
|--------|------|------|
| `&` | 按位与 | `x & 0x0F` 取低4位 |
| `\|` | 按位或 | `x \| 0xF0` 设置高4位 |
| `^` | 按位异或 | `x ^ y` |
| `~` | 按位取反 | `~x` |
| `<<` | 左移 | `x << 4` |
| `>>` | 右移 | `x >> 4` |

**注意区别：**
- `&&` 是逻辑与（布尔运算）
- `&` 是按位与（位运算）

### 1.3 条件编译

```cpp
#ifdef QM_ARM
    // ARM 特定代码
#endif

#ifdef QM_x86
    // x86 特定代码
#endif
```

---

## 二、量化基础

### 2.1 为什么需要量化？

```
FP32: 每个权重 4 字节，7B 模型 ≈ 28 GB
INT4: 每个权重 0.5 字节，7B 模型 ≈ 3.5 GB

优势：快 8 倍，省 8 倍内存！
```

### 2.2 Block-wise 量化

```
数据被分成固定大小的块，每个块有自己的 scale

原始 FP32 数据 (128 个元素):
├── Block 0 (索引 0-31)   → scale[0]
├── Block 1 (索引 32-63)  → scale[1]
├── Block 2 (索引 64-95)  → scale[2]
└── Block 3 (索引 96-127) → scale[3]

量化公式：
original_value = quantized_value × scale + offset
```

### 2.3 量化流程

```
训练时:    FP32 权重
  ↓ 量化
推理时:    INT4 权重 + Scale
  ↓ 反量化
输出:      FP32 结果
```

---

## 三、矩阵乘法基础

### 3.1 矩阵维度

```
C = A × B^T

A: m × k        B: n × k        C: m × n
┌────────┐      ┌────────┐      ┌────────┐
│ k列    │  ×   │ k列    │  =   │ n列    │
│        │      │        │      │        │
│ m行    │      │ n行    │      │ m行    │
└────────┘      └────────┘      └────────┘

C[row][col] = Σ A[row][ch] × B[col][ch]
              └─ ch: 0 到 k ─┘
```

### 3.2 内存布局

```
A 矩阵 (m × k) 的内存布局（行优先）：
┌─────────────────────────────────────┐
│ row=0: [0, 1, 2, ..., k-1]          │
│ row=1: [k, k+1, ..., 2k-1]          │
│ row=2: [2k, 2k+1, ..., 3k-1]        │
│ ...                                 │
└─────────────────────────────────────┘

访问 A[row][ch]: a_int8[row * k + ch]
```

---

## 四、Loop Unrolling（循环展开）

### 4.1 什么是循环展开？

**核心思想：** 一次迭代处理多个输出，减少循环开销。

### 4.2 对比

**❌ 普通写法：**
```cpp
for (int col = 0; col < n; col++) {
    float acc = 0;
    for (int ch = 0; ch < k; ch++) {
        acc += A[row][ch] * B[col][ch];
    }
    C[row][col] = acc;
}
```

**✅ 展开写法：**
```cpp
for (int col = 0; col < n; col += 4) {
    float acc0 = 0;  // C[row][col]
    float acc1 = 0;  // C[row][col+1]
    float acc2 = 0;  // C[row][col+2]
    float acc3 = 0;  // C[row][col+3]

    for (int ch = 0; ch < k; ch++) {
        acc0 += A[row][ch] * B[col][ch];
        acc1 += A[row][ch] * B[col+1][ch];
        acc2 += A[row][ch] * B[col+2][ch];
        acc3 += A[row][ch] * B[col+3][ch];
    }

    C[row][col]   = acc0;
    C[row][col+1] = acc1;
    C[row][col+2] = acc2;
    C[row][col+3] = acc3;
}
```

### 4.3 为什么是 4？

```
展开因子选择：2, 4, 8

| 展开因子 | 优点 | 缺点 |
|----------|------|------|
| 2 | 寄存器压力小 | 并行度不够 |
| 4 | 平衡性能和寄存器 | - |
| 8 | 并行度高 | 寄存器可能不够 |

4 是经验最优值
```

---

## 五、INT4 数据格式

### 5.1 INT4 数值范围

```
有符号 4 位整数范围：[-8, 7]

二进制    值
0000  →   0
0111  →   7
1000  →   -8
1111  →   -1
```

### 5.2 INT4 打包存储

```
1 个字节存储 2 个 INT4：

Byte: [H3 H2 H1 H0 | L3 L2 L1 L0]
        高4位         低4位

例子：0xAB = 10101011
高4位：1010 = -6
低4位：1011 = -5
```

### 5.3 INT4 解包

```cpp
uint8_t packed_byte = 0xAB;  // 10101011

// 提取高4位和低4位
int8_t w_high = packed_byte >> 4;   // 1010 = 10
int8_t w_low = packed_byte & 0x0F;   // 1011 = 11

// 符号扩展（INT4 → INT8）
w_high = (int8_t)(w_high << 4) >> 4;  // = -6
w_low = (int8_t)(w_low << 4) >> 4;    // = -5
```

**为什么需要符号扩展？**

```
直接赋值的问题：
int8_t x = 0xB;  // = 11 (错误！应该是 -5)

符号扩展：
1. 左移4位：0xB << 4 = 0xB0 (10110000)
2. 算术右移4位：0xB0 >> 4 = 0xFB (11111011) = -5 ✓
```

---

## 六、ARM vs x86 架构差异

### 6.1 SIMD 寄存器宽度

| 架构 | SIMD 技术 | 寄存器宽度 | 每次处理 |
|------|-----------|-----------|----------|
| ARM | NEON | 128 位 | 16 字节 = 32 个 INT4 |
| x86 | AVX2 | 256 位 | 32 字节 = 64 个 INT4 |

### 6.2 权重存储顺序

**ARM 重排：**
```
原始顺序： (w0,w1), (w2,w3), ..., (w30,w31)
ARM 顺序：  (w0,w16),(w1,w17),..., (w15,w31)

目的：便于 NEON 指令一次性加载
```

**x86 重排：**
```
原始顺序： (w0,w1), (w2,w3), ..., (w62,w63)
x86  顺序：  (w0,w32),(w1,w33),..., (w31,w63)

目的：便于 AVX2 指令一次性加载
```

### 6.3 循环参数

| 参数 | ARM | x86 |
|------|-----|-----|
| 循环次数 (qj) | 16 | 32 |
| 第二个索引 | 16 + qj | 32 + qj |
| 处理 block 数 | 1 | 2 |
| 累加器数量 | 4 | 8 (4 + 4_2nd) |

---

## 七、代码实现关键点

### 7.1 指针计算

```cpp
// A 矩阵：INT8，每个元素 1 字节
const signed char *a_int8 = &A->int8_data_ptr[row * k + ch];

// B 矩阵：INT4，2 个元素挤 1 字节
uint8_t *w0_int4 = &B->int4_data_ptr[(col * k + ch) / 2];

// Scale 索引计算
float s_a = params->A_scales[(row * k + ch) / block_size];
float s_w0 = params->scales[(col * k + ch) / block_size];
```

### 7.2 ARM 实现

```cpp
for (int qj = 0; qj < 16; qj++) {
    int8_t a0 = a_int8[qj];      // A[row][ch+qj]
    int8_t a1 = a_int8[16+qj];   // A[row][ch+qj+16]

    // w0_int4 → intermediate_sum0
    uint8_t pb0 = w0_int4[qj];
    int8_t w0_low = (int8_t)((pb0 & 0x0F) << 4) >> 4;
    int8_t w0_high = (int8_t)((pb0 >> 4) << 4) >> 4;
    intermediate_sum0 += w0_high * a0 + w0_low * a1;

    // 同样处理 w1_int4, w2_int4, w3_int4
}
```

### 7.3 x86 实现

```cpp
for (int qj = 0; qj < 32; qj++) {
    int8_t a0 = a_int8[qj];
    int8_t a1 = a_int8[32 + qj];

    if (qj < 16) {
        // 第一个 block
        intermediate_sum0 += ...
    } else {
        // 第二个 block
        intermediate_sum0_2nd += ...
    }
}
```

---

## 八、常见误区与纠正

### 误区 1：混淆 ch 和 col

**错误理解：** `a_int8[row*k+col]`

**正确理解：**
- `ch` 是求和维度（A 的列，B 的列）
- `col` 是 C 的列（对应 B 的行）

### 误区 2：不理解 block_size 的作用

**错误理解：** `s_a` 是 A 整体的 scale

**正确理解：** `s_a` 是按 block 的 scale
```cpp
block_index = (row * k + ch) / block_size;
s_a = params->A_scales[block_index];
```

### 误区 3：不理解 INT4 打包

**错误理解：** 直接读取 INT4 值

**正确理解：** 需要从字节中解包
```cpp
// 1 字节 = 2 个 INT4
uint8_t packed_byte = w_int4[qj];
int8_t w_low = packed_byte & 0x0F;    // 低 4 位
int8_t w_high = packed_byte >> 4;     // 高 4 位
```

### 误区 4：符号扩展错误

**错误写法：** `&&` 而不是 `&`
```cpp
// ❌ 错误
int8_t w_low = packed_byte && 0x0F;  // 逻辑与，结果是 0 或 1

// ✅ 正确
int8_t w_low = packed_byte & 0x0F;   // 按位与
```

### 误区 5：不理解 ARM/x86 重排

**错误理解：** `w_low` 对应 `w1`

**正确理解：**
```
ARM: Byte[qj] = [w_qj | w_qj+16]
x86: Byte[qj] = [w_qj | w_qj+32]

w_high = w_qj, w_low = w_qj+16 (ARM) 或 w_qj+32 (x86)
```

---

## 九、代码层次理解

```
┌─────────────────────────────────────────────────────────┐
│ Level 1: 外层 - 多线程分工                              │
│   每个线程处理 C 矩阵的一部分列 [start, end)            │
├─────────────────────────────────────────────────────────┤
│ Level 2: 中层 - 循环展开                                │
│   每次迭代同时计算 4 列 (col, col+1, col+2, col+3)      │
├─────────────────────────────────────────────────────────┤
│ Level 3: 内层 - 块处理                                  │
│   每次处理 32/64 个权重 (1/2 个 block)                 │
├─────────────────────────────────────────────────────────┤
│ Level 4: 底层 - INT4 解包和乘累加                        │
│   从字节中提取 INT4，符号扩展，与 INT8 相乘累加          │
└─────────────────────────────────────────────────────────┘
```

---

## 十、总结

### 关键要点

1. **量化**：INT4 权重 + Block-wise scale
2. **循环展开**：一次计算 4 列，减少循环开销
3. **INT4 解包**：从字节中提取 2 个 INT4，需要符号扩展
4. **架构差异**：ARM (128位) vs x86 (256位)
5. **内存布局**：权重重排以适配 SIMD 指令

### 学习路径

```
1. 理解基础：C++ 指针、位运算
2. 理解量化：为什么需要，如何实现
3. 理解循环展开：为什么展开，展开多少
4. 理解 INT4：如何打包、解包、符号扩展
5. 理解架构差异：ARM vs x86 的不同
6. 实践：完成 loop_unrolling.cc
```

---

*创建日期：2026-03-24*
*最后更新：2026-03-24*