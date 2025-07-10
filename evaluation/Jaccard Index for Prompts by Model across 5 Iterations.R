library(jsonlite)
library(dplyr)
library(ggplot2)

data <- fromJSON('query_jaccard.json')
prmpt_order <- list(
  'Children of Johann Sebastian Bach' = 1,
  'List of US presidents' = 2,
  'List of non-fictional US presidents' = 3,
  'List of US presidents since 1970' = 4,
  'List of non-fictional US presidents since 1970' = 5,
  'For all US presidencies that started after 1970, give the serving president and the start date' = 6,
  'list all physics nobel laureates from 2000 to 2010' = 7,
  'When did Niels Bohr win a Nobel Prize?' = 8,
  'When did Richard Feynman win a Nobel Prize?' = 9,
  'list all physics nobel laureates who won their prize after Niels Bohr but before Richard Feynman' = 10,
  'list all physics nobel laureates who won their prize after Niels Bohr but before Richard Feynman! This query gives Niels Bohrs date: \nSELECT ?date\nWHERE {\nwd:Q7085 p:P166 ?statement .\n?statement ps:P166 ?award .\n?award wdt:P279 wd:Q7191 .\n?statement pq:P585 ?date .\n}\n, this query gives Richard Feynmans date: \nSELECT ?date\nWHERE {\nwd:Q39246 p:P166 ?statement .\n?statement ps:P166 ?award .\n?award wdt:P279 wd:Q7191 .\n?statement pq:P585 ?date .\n}\n, and this query gives all physics nobel laureates from 2000 to 2010: \nSELECT DISTINCT ?laureateLabel\nWHERE {\n?laureate wdt:P31 wd:Q5 ;\np:P166 ?awardStatement . \n?awardStatement ps:P166 wd:Q38104 ;\npq:P585 ?awardDate .\nFILTER (YEAR(?awardDate) >= 2000 && YEAR(?awardDate) <= 2010)\nSERVICE wikibase:label {\nbd:serviceParam wikibase:language "[AUTO_LANGUAGE],en".\n}\n}\nORDER BY ?awardDate ?laureateLabel\n' = 11,
  'list the grand children of Queen Elisabeth II' = 12,
  'list the countries where the Summer Olympics were held between 2008 and 2022, along with the year' = 13,
  'list the countries where the Winter Olympics were held between 2008 and 2022, along with the year' = 14,
  'list the countries where the Olympics were held between 2008 and 2022, along with the year' = 15,
  'list the countries where the Summer- or Winter Olympics were held between 2008 and 2022, along with the year' = 16
)

custom_order_df <- data.frame(
  prompt = names(prmpt_order),
  prompt_id = unlist(prmpt_order),
  stringsAsFactors = FALSE
)

plot_data <- data %>%
  select(model, prompt, iteration, jaccard_index) %>%
  left_join(custom_order_df, by = "prompt") %>%
  mutate(iteration = as.factor(iteration)) %>%
  mutate(jaccard_index = ifelse(jaccard_index == 0, NA, jaccard_index)) # Replace jaccard_index of 0 with NA so it actually shows no bars instead of very very tiny ones even though that should not be standard behaviour anyways what the f and also why does it show it correctly in the preview even without this line but then in the pdf export it suddenly does make a difference???


jac_index <- ggplot(plot_data, aes(x = as.factor(prompt_id), y = jaccard_index, fill = iteration)) +
  geom_bar(stat = "identity", position = position_dodge(width = 0.8), width = 0.7) +
  geom_vline(xintercept = seq(from = 1.5, to = max(plot_data$prompt_id, na.rm = TRUE) - 0.5, by = 1),
             color = "gray", linetype = "dashed", size = 0.5) +
  labs(
    title = "Jaccard Index for Prompts by Model across 5 Iterations",
    x = "Prompt",
    y = "Jaccard Index",
    fill = "Iteration"
  ) +
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
    axis.text.x = element_text(),
    axis.text.y = element_text(),
    legend.title = element_text(size = 10, face = "bold"),
    legend.text = element_text(size = 9)
  ) +
  facet_wrap(~ model, ncol = 1)

jac_index


# Save as pdf
pdf_output_path <- "jac_index.pdf"

ggsave(filename = pdf_output_path,
       plot = jac_index,
       width = 21,
       height = 10,
       units = "cm",
       dpi = 1200)

cat(paste0("Jac index saved to: ", pdf_output_path, "\n"))