# ns1_biosensor_script.R
# Script: Tính tỉ lệ % KET_QUA_NS1_BIOSENSOR theo TINH và vẽ biểu đồ bằng ggplot2
# Yêu cầu: đặt file "NS1_Biosensor_no_diacritics.csv" cùng thư mục với file R này
#
# Nội dung: - nạp thư viện
#          - đọc dữ liệu
#          - tính tổng mẫu & phần trăm theo TINH x KET_QUA_NS1_BIOSENSOR
#          - tạo nhãn "TINH (n)"
#          - vẽ biểu đồ stacked bar chart và lưu file ảnh

# --- CÀI ĐẶT / NẠP THƯ VIỆN ---
# Nếu chạy lần đầu và thiếu package, bỏ comment các dòng install.packages(...) sau đây:
# install.packages(c("dplyr", "ggplot2", "readr", "scales", "forcats", "tidyr"))

library(dplyr)
library(ggplot2)
library(readr)
library(scales)
library(forcats)
library(tidyr)

# --- ĐỌC DỮ LIỆU ---
csv_path <- "NS1_Biosensor_no_diacritics.csv"

if (!file.exists(csv_path)) {
  stop(paste0("File not found: ", csv_path, ". Vui lòng đặt file CSV cùng thư mục với script này."))
}

df <- read_csv(csv_path, show_col_types = FALSE)

# --- TIỀN XỬ LÝ & TÍNH TOÁN ---
# Chuẩn hóa cột kết quả và tỉnh
df <- df %>%
  mutate(
    KET_QUA_NS1_BIOSENSOR = ifelse(is.na(KET_QUA_NS1_BIOSENSOR), "Unknown", as.character(KET_QUA_NS1_BIOSENSOR)),
    KET_QUA_NS1_BIOSENSOR = trimws(KET_QUA_NS1_BIOSENSOR),
    TINH = trimws(as.character(TINH))
  )

# Tính tổng số mẫu theo tỉnh
df_n <- df %>%
  group_by(TINH) %>%
  summarise(total_n = n(), .groups = "drop")

# Tính số mẫu & phần trăm theo TINH x KET_QUA
df_percent <- df %>%
  group_by(TINH, KET_QUA_NS1_BIOSENSOR) %>%
  summarise(n = n(), .groups = "drop") %>%
  group_by(TINH) %>%
  mutate(percentage = n / sum(n) * 100) %>%
  ungroup() %>%
  left_join(df_n, by = "TINH") %>%
  filter(total_n > 0)

# Tạo nhãn TINH (ví dụ: "Ben Tre (20)")
df_percent <- df_percent %>%
  mutate(TINH_label = paste0(TINH, " (", total_n, ")"))

# Sắp xếp trục X theo tổng mẫu giảm dần (tuỳ chọn)
tinh_order <- df_percent %>%
  distinct(TINH, total_n, TINH_label) %>%
  arrange(desc(total_n)) %>%
  pull(TINH_label)

df_percent <- df_percent %>%
  mutate(TINH_label = factor(TINH_label, levels = tinh_order))

# --- VẼ BIỂU ĐỒ ---
# Chọn màu cho các nhãn phổ biến Positive/Negative
fill_vals <- c("Positive" = "#D73027", "Negative" = "#4575B4")

p <- ggplot(df_percent, aes(x = TINH_label, y = percentage, fill = KET_QUA_NS1_BIOSENSOR)) +
  geom_col(position = "stack", width = 0.7) +
  geom_text(
    aes(label = ifelse(percentage >= 3, paste0(round(percentage,1), "%"), "")),
    position = position_stack(vjust = 0.5),
    size = 3.2,
    color = "white"
  ) +
  scale_y_continuous(expand = expansion(c(0,0.02)), limits = c(0, 100)) +
  scale_fill_manual(values = fill_vals, na.value = "grey70") +
  labs(
    title = "Tỉ lệ % kết quả NS1 Biosensor theo tỉnh",
    subtitle = "Mỗi cột: tỉnh (số mẫu n). Các phần thể hiện % Positive / Negative",
    x = "Tỉnh (số mẫu n)",
    y = "Tỉ lệ (%)",
    fill = "Kết quả NS1"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    axis.text.x = element_text(angle = 45, hjust = 1),
    legend.position = "top",
    plot.title = element_text(face = "bold")
  )

# In plot ra màn hình (nếu chạy tương tác)
print(p)

# Lưu ảnh (PNG) vào thư mục hiện hành
out_png <- "ns1_biosensor_percent_by_tinh.png"
ggsave(out_png, plot = p, width = 12, height = 6, dpi = 300)

# Ngoài ra lưu bảng tóm tắt (CSV) nếu muốn
summary_tbl <- df_percent %>%
  select(TINH, TINH_label, KET_QUA_NS1_BIOSENSOR, n, percentage) %>%
  pivot_wider(
    names_from = KET_QUA_NS1_BIOSENSOR,
    values_from = c(n, percentage),
    values_fill = 0
  ) %>%
  arrange(desc(as.numeric(gsub(".*\\((\\d+)\\)$", "\\1", TINH_label))))

write_csv(summary_tbl, "ns1_biosensor_summary_by_tinh.csv")

cat("Hoàn tất: Đã tạo ảnh", out_png, "và bảng tóm tắt ns1_biosensor_summary_by_tinh.csv\n")
