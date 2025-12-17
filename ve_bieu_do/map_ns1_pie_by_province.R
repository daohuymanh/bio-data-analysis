# map_ns1_pie_by_province.R
# Vẽ bản đồ VN + pie charts tại mỗi tỉnh thể hiện tỉ lệ Positive/Negative của KET_QUA_NS1_BIOSENSOR
# Yêu cầu: file NS1_Biosensor_no_diacritics.csv ở cùng thư mục hoặc chỉnh đường dẫn csv_path

# --- CÀI ĐẶT / NẠP THƯ VIỆN ---
# Nếu chạy lần đầu, bỏ comment để cài đặt packages cần thiết
# install.packages(c("sf","dplyr","readr","ggplot2","scatterpie","geodata","stringr","scales"))

library(sf)
library(dplyr)
library(readr)
library(ggplot2)
library(scatterpie)  # vẽ pie charts trên bản đồ
library(geodata)     # để tải GADM (hoặc thay bằng shapefile sẵn có)
library(stringr)
library(scales)

# --- THAM SỐ ---
csv_path <- "NS1_Biosensor_no_diacritics.csv"   # chỉnh nếu file nằm chỗ khác
gadm_path <- tempdir()   # thư mục lưu GADM
gadm_level <- 1          # level 1 = tỉnh

# --- ĐỌC DỮ LIỆU ---
df <- read_csv(csv_path, show_col_types = FALSE)

# Kiểm tra cột cần thiết tồn tại
if (!all(c("TINH", "KET_QUA_NS1_BIOSENSOR") %in% colnames(df))) {
  stop("CSV thiếu cột TINH hoặc KET_QUA_NS1_BIOSENSOR")
}

# Chuẩn hoá text
df <- df %>%
  mutate(
    TINH = str_squish(as.character(TINH)),
    TINH_lower = tolower(TINH),
    KET_QUA_NS1_BIOSENSOR = ifelse(is.na(KET_QUA_NS1_BIOSENSOR), "Unknown", as.character(KET_QUA_NS1_BIOSENSOR)),
    KET_QUA_NS1_BIOSENSOR = str_squish(KET_QUA_NS1_BIOSENSOR)
  )

# --- TỔNG HỢP SỐ LIỆU THEO TỈNH ---
df_counts <- df %>%
  group_by(TINH, KET_QUA_NS1_BIOSENSOR) %>%
  summarise(n = n(), .groups = "drop") %>%
  group_by(TINH) %>%
  mutate(total_n = sum(n),
         pct = n / total_n * 100) %>%
  ungroup()

# Chuyển sang wide để vẽ pie (các cột Positive & Negative)
df_wide <- df_counts %>%
  select(TINH, KET_QUA_NS1_BIOSENSOR, n) %>%
  tidyr::pivot_wider(names_from = KET_QUA_NS1_BIOSENSOR, values_from = n, values_fill = 0)

# rename common labels nếu cần (ví dụ "Positive"/"Negative")
# kiểm tra các nhãn duy nhất
cat("Những nhãn KET_QUA_NS1_BIOSENSOR tìm thấy:\n")
print(unique(df$KET_QUA_NS1_BIOSENSOR))

# --- LẤY SHAPE TỈNH VIỆT NAM TỪ GADM ---
# Tải GADM (lưu về gadm_path). Lưu ý: cần internet để tải lần đầu
cat("Tải GADM level 1 cho Vietnam (nếu chưa có)\n")
gadm <- geodata::gadm(country = "VNM", level = 1, path = "GADM/", version = "4.0")
gadm_vn <- tryCatch(sf::st_as_sf(gadm),error = function(e) NULL)
                       
# Xem tên cột tên tỉnh trong shapefile (thường là NAME_1)
print(names(gadm_vn))
# Thường tên tỉnh nằm ở cột VARNAME_1
if (!"VARNAME_1" %in% names(gadm_vn)) {
  stop("Không tìm thấy cột NAME_1 trong GADM - kiểm tra shapefile")
}

gadm_vn <- gadm_vn %>% mutate(VARNAME_1_lower = tolower(trimws(VARNAME_1)))

# --- KHỚP TÊN TỈNH GIỮA CSV VÀ SHAPE ---
# Thử khớp trực tiếp bằng lowercase
df_join <- df_wide %>%
  mutate(TINH_lower = tolower(trimws(TINH))) %>%
  left_join(gadm_vn %>% select(ID_1 = ID_1, VARNAME_1, VARNAME_1_lower, geometry), by = c("TINH_lower" = "VARNAME_1_lower"))

# Những tỉnh chưa khớp
not_matched <- df_join %>% filter(is.na(ID_1)) %>% distinct(TINH) %>% pull(TINH)
if (length(not_matched) > 0) {
  cat("Các TINH không khớp tên tự động (bạn có thể map tay):\n")
  print(not_matched)
} else {
  cat("Tất cả TINH đã khớp tự động với shapefile.\n")
}

# Nếu có tỉnh không khớp, bạn có thể cung cấp bảng map tay; ví dụ:
# manual_map <- tibble::tribble(
#   ~TINH, ~NAME_1,
#   "TP. Can Tho", "Cần Thơ",
#   "Ben Tre", "Bến Tre"
# )
# Sau đó join theo manual_map -> NAME_1 -> gadm

# Ví dụ minh họa: cố gắng chỉnh 1 vài tên hay gặp (bạn hãy chỉnh theo dữ liệu thực tế)
# Tạo hàm mapping đơn giản (bổ sung nếu cần)
manual_map <- tibble::tibble(
  TINH = c("TP. Can Tho", "TP. HCM", "HCM", "Ha Noi", "TP. Ha Noi"),
  NAME_1 = c("Cần Thơ", "Hồ Chí Minh", "Hồ Chí Minh", "Hà Nội", "Hà Nội")
)

if (length(not_matched) > 0) {
  tmp <- df_wide %>% mutate(TINH_lower = tolower(trimws(TINH)))
  # Nếu manual_map chứa mapping thì apply
  if (exists("manual_map")) {
    tmp2 <- tmp %>% left_join(manual_map, by = "TINH")
    # nếu có VARNAME_1 từ manual_map, join vào gadm
    tmp2 <- tmp2 %>% mutate(VARNAME_1_join = ifelse(!is.na(VARNAME_1), VARNAME_1, NA))
    tmp2 <- tmp2 %>% left_join(gadm_vn %>% select(VARNAME_1, VARNAME_1_lower), by = c("VARNAME_1_join" = "VARNAME_1"))
    # now merge back where mapped
    mapped_names <- tmp2 %>% filter(!is.na(VARNAME_1_lower)) %>% select(TINH, VARNAME_1)
    if (nrow(mapped_names) > 0) {
      # apply mapping to df_wide
      df_wide <- df_wide %>% left_join(mapped_names, by = "TINH")
      # if NAME_1 present, join to gadm by NAME_1
      df_join <- df_wide %>% 
        mutate(VARNAME_1_lower = ifelse(is.na(VARNAME_1), tolower(trimws(TINH)), tolower(trimws(VARNAME_1)))) %>%
        left_join(gadm_vn %>% select(ID_1, VARNAME_1, VARNAME_1_lower, geometry), by = c("VARNAME_1_lower" = "VARNAME_1_lower"))
    }
  }
}

# Nếu vẫn chưa match nhiều, in gợi ý mapping cho bạn
if (any(is.na(df_join$GID_1))) {
  cat("Sau cố gắng tự động/manual, vẫn còn các TINH không match. In bảng TINH có thể bạn cần sửa:\n")
  print(df_wide %>% filter(!tolower(TINH) %in% gadm_vn$VARNAME_1_lower) %>% distinct(TINH))
}

# Giữ những bản ghi đã match
df_mapped <- df_join %>% filter(!is.na(GID_1))

# Nếu không có gì match, dừng lại
if (nrow(df_mapped) == 0) stop("Không có tỉnh nào match với shapefile. Vui lòng chỉnh lại mapping thủ công.")


                    


# --- LẤY TỌA ĐỘ CENTROID CHO MỖI TỈNH ĐỂ ĐẶT PIE ---
# chuyển gadm_vn sang sf với crs phù hợp
gadm_vn_sf <- st_as_sf(gadm_vn)

# Centroid (dùng st_point_on_surface để đảm bảo centroid nằm trong polygon)
centroids <- st_point_on_surface(gadm_vn_sf)
centroids_coords <- st_coordinates(centroids)

gadm_centroids <- gadm_vn_sf %>%
  mutate(
    lon = centroids_coords[,1],
    lat = centroids_coords[,2]
  ) %>%
  st_drop_geometry() %>%
  select(VARNAME_1, lon, lat) %>%
  mutate(VARNAME_1_lower = tolower(VARNAME_1))

# Join to df_mapped by NAME_1
df_plot <- df_mapped %>%
  # if joined by GID_1 earlier, we can match by NAME_1
  left_join(gadm_centroids, by = c("VARNAME_1" = "VARNAME_1"))  # try direct
# fallback join by lowercase if needed
if (any(is.na(df_plot$lon))) {
  df_plot <- df_mapped %>%
    left_join(gadm_centroids, by = c("VARNAME_1_lower" = "VARNAME_1_lower"))
}

# Có thể vẫn còn NA lon nếu mapping không tốt
if (any(is.na(df_plot$lon))) {
  cat("Một số tỉnh chưa có centroid (lon/lat) do mapping tên chưa chính xác. In danh sách:\n")
  print(df_plot %>% filter(is.na(lon)) %>% distinct(TINH))
  # bạn có thể gán toạ độ thủ công nếu cần
}

# --- TẠO DỮ LIỆU PIE: đảm bảo có cột Positive & Negative (hoặc các nhãn hiện có) ---
# Xác định tên cột kết quả thực tế trong df_plot wide
pie_cols <- setdiff(colnames(df_plot), c("TINH","TINH_lower","VARNAME_1","VARNAME_1_lower","ID_1","total_n","pct","lon","lat","geometry"))
# But simpler: rebuild a tidy pie df with standard columns "Positive" and "Negative"
pie_df <- df_counts %>%
  select(TINH, KET_QUA_NS1_BIOSENSOR, n) %>%
  tidyr::pivot_wider(names_from = KET_QUA_NS1_BIOSENSOR, values_from = n, values_fill = 0) %>%
  left_join(df_plot %>% select(TINH, lon, lat, total_n), by = "TINH")

# For safety, if column names have spaces or different labels, check:
cat("Columns for pie (examples):\n")
print(names(pie_df))

# If your data uses "Positive"/"Negative" labels, keep them; otherwise adapt the next line
# Ensure columns 'Positive' and 'Negative' exist; if not, try find similar names
if (!("Positive" %in% names(pie_df) && "Negative" %in% names(pie_df))) {
  cat("Dữ liệu không có cả 2 cột 'Positive' và 'Negative' sau pivot. Cột hiện có:\n")
  print(names(pie_df))
  cat("Bạn cần sửa tên cột hoặc kiểm tra nhãn trong KET_QUA_NS1_BIOSENSOR.\n")
  # attempt to find columns containing "Pos" or "Neg"
}

# Replace NA lon/lat to avoid plotting errors
pie_df <- pie_df %>% filter(!is.na(lon) & !is.na(lat))

# --- HOÀNG SA & TRƯỜNG SA (thêm điểm nhỏ) ---
# Coordinates approximate (center points)
# Hoàng Sa (Paracel): ~16.5N, 112.0E
# Trường Sa (Spratly): ~8.8N, 114.4E
islands <- tibble::tibble(
  name = c("Hoang Sa", "Truong Sa"),
  lon = c(112.0, 114.4),
  lat = c(16.5, 8.8),
  Positive = c(0, 0),  # nếu có dữ liệu muốn hiển thị, bạn có thể chỉnh
  Negative = c(0, 0),
  total_n = c(0, 0)
)

# --- VẼ BẢN ĐỒ VỚI PIE CHARTS (dùng scatterpie) ---
# Thiết lập độ lớn pie theo căn bản sqrt(total_n) để tỉ lệ mắt dễ nhìn
pie_df <- pie_df %>% mutate(size = scales::rescale(sqrt(total_n), to = c(0.6, 4))) # adjust min/max size

# Merge islands nếu bạn muốn hiển thị pie (ở đây size = small)
islands$size <- 0.8
all_pies <- bind_rows(
  pie_df %>% mutate(source = "province"),
  islands %>% rename(TINH = name) %>% mutate(source = "island")
)

# Plot
p <- ggplot() +
  geom_sf(data = gadm_vn_sf, fill = "#f2f2f2", color = "grey60", size = 0.3) +
  geom_scatterpie(
    aes(x = lon, y = lat, r = size),
    data = all_pies,
    cols = c("Positive", "Negative"),
    color = NA, alpha = 0.85
  ) +
  # Add borders around pies
  geom_scatterpie_legend(range(all_pies$size, na.rm = TRUE), x = 102, y = 5) +
  scale_fill_manual(values = c("Positive" = "#D73027", "Negative" = "#4575B4"), na.value = "grey80") +
  coord_sf(xlim = c(102, 116), ylim = c(6, 23), expand = FALSE) +  # adjust bbox to include islands
  labs(
    title = "Tỉ lệ % KET_QUA_NS1_BIOSENSOR theo tỉnh (pie trên mỗi tỉnh)",
    subtitle = "Kích thước pie tỷ lệ với sqrt(số mẫu). Bao gồm Hoàng Sa & Trường Sa (toạ độ xấp xỉ).",
    caption = "Nguồn: NS1_Biosensor_no_diacritics.csv"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    legend.position = "right",
    panel.background = element_rect(fill = "aliceblue"),
    panel.grid.major = element_line(color = "transparent")
  )

print(p)

# Lưu ảnh
ggsave("vn_ns1_pies_map.png", p, width = 10, height = 8, dpi = 300)
cat("Lưu ảnh ở vn_ns1_pies_map.png\n")
