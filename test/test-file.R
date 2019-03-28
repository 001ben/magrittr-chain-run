library(data.table)
library(magrittr)
library(dplyr)

filtered_averages <- mtcars %>%
  as_tibble %>%
  filter(wt>=2 & vs==0
         ) %>%
  .[, lapply(.SD, mean), .SDcols=names(.)] # Yay test passed

longer_list <- mtcars %>%
  data.table %>%
  .[cyl==6] %>%
  .[, .(median(disp),
        median(drat),
        median(wt))]

mtcars %>%
  data.table %>%
  .[, mean(vs)] -> vs_mean
