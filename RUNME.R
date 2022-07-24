# Bootstrapping residual cutoffs ####

# source the function for bootstrapping residuals:
source("bootstrap_median_residuals.R")

# run the function on the master_dentition.csv dataset from the paper
example_teeth <- bootstrap_median_residuals(bootstraps = 1000,
                                   dentition_file = "master_dentition.csv",
                                   stress_column = 10,
                                   position_column = 6,
                                   jawlength_column = 4)
# we have five things here:
# 1. the bootstrapped residuals
summary(example_teeth)
hist(example_teeth$bootstrapped.residuals, breaks = 100, 
     xlab = "Residual", main = "Bootstrapped residuals")

# 2. the standard deviation (in units of median stress):
example_teeth$sd

# 3. the 95th quantile cutoff:
abline(v = c(-example_teeth$q95, example_teeth$q95), col = "red", lty = 2)

# 4. the kmeans cutoff:
abline(v = c(-example_teeth$kmeans, example_teeth$kmeans),
       col = "blue", lty = 3)

# 5. and the original dataset, plus normalized stress, position, and residuals:
example_teeth$original.teeth


# Applying cutoffs to an individual jaw ####
library(ggplot2)
ophiodon <- example_teeth$original.teeth$`Ophiodon elongatus;Lower Jaw`

color <- "darkgreen"
p1 <- ggplot(ophiodon, aes(x = Position.norm, y = Stress.norm)) +
  geom_hline(yintercept = median(ophiodon$Stress.norm), color = grey(0.4, alpha = 0.8), lwd = 1.5) +
  geom_point(size = 5, pch = 21, color = alpha(color, 0.9), fill = alpha(color, 0.5)) +
  ylab(expression(paste("Stress (normalized)"))) +
  xlab("Jaw position (% from joint)") +
  ggtitle(expression(italic("Ophiodon elongatus"))) +
  scale_y_continuous(labels = function(x) format(x, scientific = TRUE)) +
  theme_bw(base_size = 15); p1

# relative to the 95th quantile and kmeans cutoffs:
p2 <- p1 + geom_hline(yintercept = c(-example_teeth$q95,
                                     example_teeth$q95),
                      col = "red", lty = 2) +
  geom_hline(yintercept = c(-example_teeth$kmeans,
                            example_teeth$kmeans),
             col = "blue", lty = 3); p2

# so in this case, Ophiodon has one tooth which exceeds the 95% quantile
# cutoff, but not the kmeans cutoff

# we can see which tooth:
tooth_idx <- which(abs(ophiodon$Stress.norm) > example_teeth$q95)
ophiodon[tooth_idx, ]
