library(data.table)
library(magrittr)

filtered_averages <- mtcars %>%
  data.table %>%
  .[wt>=2 & vs==0] %>%
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
