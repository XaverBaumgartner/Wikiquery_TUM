library(tidyverse) # Includes ggplot2 and tidyr

# --- Data Preparation ---
data_raw <- tribble(
  ~Iteration, ~Model, ~Precision, ~Recall, ~F1_macro, ~F1_micro, ~Global_Jaccard, ~Average_Jaccard,
  1, "gemini", 0.6146, 0.5625, 0.5777, 0.7326, 0.5780, 0.5521,
  1, "gemini_finetune", 0.1696, 0.1875, 0.1771, 0.5328, 0.3631, 0.1696,
  1, "gemini_finetune_mcp", 0.4938, 0.4326, 0.4340, 0.6250, 0.4545, 0.4275,
  1, "gemini_mcp", 0.8580, 0.8625, 0.8598, 0.8776, 0.7819, 0.8474,
  
  2, "gemini", 0.3540, 0.3438, 0.3421, 0.5786, 0.4071, 0.3228,
  2, "gemini_finetune", 0.2321, 0.2500, 0.2396, 0.5067, 0.3393, 0.2321,
  2, "gemini_finetune_mcp", 0.4375, 0.3451, 0.3569, 0.4412, 0.2830, 0.3451,
  2, "gemini_mcp", 0.7827, 0.8063, 0.7929, 0.7885, 0.6509, 0.7776,
  
  3, "gemini", 0.5000, 0.4625, 0.4759, 0.6352, 0.4654, 0.4625,
  3, "gemini_finetune", 0.2946, 0.2812, 0.2812, 0.5198, 0.3512, 0.2634,
  3, "gemini_finetune_mcp", 0.3571, 0.3187, 0.3134, 0.3771, 0.2324, 0.3009,
  3, "gemini_mcp", 0.6809, 0.7375, 0.6910, 0.8071, 0.6766, 0.6715,
  
  4, "gemini", 0.6813, 0.6500, 0.6604, 0.9349, 0.8777, 0.6449,
  4, "gemini_finetune", 0.1250, 0.1250, 0.1250, 0.3394, 0.2044, 0.1250,
  4, "gemini_finetune_mcp", 0.4790, 0.4389, 0.4282, 0.7256, 0.5693, 0.4179,
  4, "gemini_mcp", 0.8267, 0.8625, 0.8390, 0.8655, 0.7629, 0.8162,
  
  5, "gemini", 0.4318, 0.4000, 0.4104, 0.5197, 0.3511, 0.3943,
  5, "gemini_finetune", 0.2321, 0.2500, 0.2396, 0.5067, 0.3393, 0.2321,
  5, "gemini_finetune_mcp", 0.5000, 0.4389, 0.4402, 0.5513, 0.3805, 0.4389,
  5, "gemini_mcp", 0.6761, 0.6750, 0.6753, 0.8406, 0.7250, 0.6656
)

data_raw$Model <- factor(data_raw$Model, levels = c("gemini_finetune", "gemini", "gemini_finetune_mcp", "gemini_mcp"))

data_long <- data_raw %>%
  pivot_longer(
    cols = c(Precision, Recall, F1_macro, F1_micro, Global_Jaccard, Average_Jaccard),
    names_to = "Metric",
    values_to = "Value"
  )

data_long$Metric <- factor(data_long$Metric,
                           levels = c("Precision", "Recall", "F1_macro", "F1_micro", "Global_Jaccard", "Average_Jaccard"),
                           labels = c("Precision", "Recall", "F1-macro", "F1-micro", "Global Jaccard", "Avg. Jaccard"))

plot_all_metrics <- ggplot(data_long, aes(x = Model, y = Value, fill = Metric)) +
  geom_boxplot(position = position_dodge(width = 0.7), width = 0.6, alpha = 0.8) +
  geom_point(position = position_dodge(width = 0.7), alpha = 1, size = 1.5, color = "black") +
  labs(
    title = "Distribution of Performance Metrics across Models (5 Iterations)",
    x = "Model Variant",
    y = "Score",
    fill = "Metric"
  ) +
  scale_y_continuous(limits = c(0, 1), breaks = seq(0, 1, by = 0.1)) +
  theme_minimal() +
  theme(
    plot.title = element_text(
      hjust = 0.5,
      face = "bold",
      size = 14,
      margin = margin(b = 15)
    ),
    axis.title.x = element_text(size = 12, margin = margin(t = 15)),
    axis.title.y = element_text(size = 12, margin = margin(r = 10)),
    axis.text.x = element_text(size = 10),
    axis.text.y = element_text(size = 10),
    legend.title = element_text(size = 10, face = "bold"),
    legend.text = element_text(size = 9)
  ) +
  scale_fill_brewer(palette = "Paired")

plot_all_metrics
# Save as pdf
pdf_output_path <- "boxplot.pdf"

ggsave(filename = pdf_output_path,
       plot = plot_all_metrics,
       width = 10,
       height = 5,
       units = "in",
       dpi = 1200)

cat(paste0("Boxplot saved to: ", pdf_output_path, "\n"))