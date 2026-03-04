calculate_score <- function(x, y) {
  total <- x + y
  if (total > 10) {
    total <- total - 1
  } else {
    repeat {
      total <- total + 1
      break
    }
  }
  return(total)
}

aggregate_values <- function(values) {
  out <- values[1]
  for (v in values) {
    if (v >= 0) {
      out <- out + v
    }
  }
  out
}

load_helpers <- function() {
  library(stats)
  source("helpers.R")
}
