bootstrap_median_residuals <- function(bootstraps = 10e3, 
                                       dentition_subsample = 0.5,
                                       dentition_file = "",
                                       stress_column = NA,
                                       position_column = NA,
                                       jawlength_column = NA) {
  
  # BOOKKEEPING ####
  library(ggplot2)
  
  if (dentition_file == "") {
    dentition_file <- file.choose()
  }
  
  # Hardcoded variables
  n.bs <- bootstraps # number of bootstrap samples per dentition
  p.teeth <- dentition_subsample # proportion of teeth within a dentition to sample within each bootstrap
  
  # read in whole dataframe 
  all.teeth <- read.csv(dentition_file) # loads the all.teeth dataframe
  
  # identifying column names
  
  # prompt user input for relevant columns
  get_column <- function(pattern = "stress", col_idx = NA)
  { 
    if (!is.na(col_idx)) {
      n <- col_idx
    } else {
      n <- grep(pattern, tolower(colnames(all.teeth)))
      
      if (length(n) != 1 ) {
        prompt <- paste("Enter the column number that contains the original", 
                        pattern, "values: ")
        n <- readline(prompt = prompt)
        if(!grepl("^[0-9]+$", n))
        {
          message("Input must be a number.")
          return(get_column())
        }
      }
    }
 
    return(as.integer(n))
    return(n)
  }
  
  # get stress index
  s <- as.numeric(get_column("stress", col_idx = stress_column))
  p <- as.numeric(get_column("position", col_idx = position_column))
  l <- as.numeric(get_column("length", col_idx = jawlength_column))

  # Read in & sort data ####
  
  # get a list of unique dentitions (combinations of species and jaw)
  unique.dentitions <- unique(paste(all.teeth$Species, all.teeth$Jaw.ID, sep = ";"))
  
  # make a list for storing them separately
  teeth.list <- setNames(vector("list", length(unique.dentitions)),
                         unique.dentitions)
  
  # for each dentition, calculate median-normalized stress
  # and distance from median stress for each tooth
  for (i in 1:length(teeth.list)) {
    
    # get the species name and jaw ID
    jawID <- unlist(strsplit(names(teeth.list)[i], ";"))
    
    # get row indices for dentitions
    tooth.idx <- which(all.teeth$Species == jawID[1] &
                         all.teeth$Jaw.ID == jawID[2])
    
    # extract those teeth from the dataframe
    dentition.df <- all.teeth[tooth.idx, ]
    
    # remove NA rows
    dentition.df <- na.omit(dentition.df)
    
    # generate median-normalized stress values
    dentition.df$Stress.norm <- dentition.df[ , s] / median(dentition.df[ , s])
    
    # generate position as a proportion of jaw length
    dentition.df$Position.norm <- dentition.df[ , p] / dentition.df[ , l] * 100
    
    # calculate median residuals
    dentition.residuals <- dentition.df$Stress.norm - median(dentition.df$Stress.norm)
    
    # add them as a new column
    dentition.df$Residuals <- dentition.residuals
    
    # add that to the teeth.list object
    teeth.list[[i]] <- dentition.df
  }
  
  # convert to a dataframe
  all.teeth.df <- do.call(rbind.data.frame, teeth.list)
  
  # for each dentition....
  for (i in 1:length(teeth.list)) {
    
    # extract teeth
    dentition.df <- teeth.list[[i]]
    
    # figure out how many teeth to use each time (round up if odd)
    sample.size <- round(p.teeth * nrow(dentition.df), digits = 0)
    
    # if we want 1000 total teeth per fish, not 1000 replicates of each dentition
    # (otherwise fish with more teeth are overrepresented)
    
    # I tested both ways -- you get the same cutoffs
    replicates <- round(n.bs / sample.size, digits = 0)
    
    j <- 0
    
    if (i == 1) {
      m.residual.vec <- c()
    }
    
    while (j < replicates) { # change to j < replicates to have the same number of residuals per dentition
      
      # sample 50% of the teeth (w/o replacement)
      dentition.sampled <- dentition.df[sample(1:nrow(dentition.df),
                                               sample.size, 
                                               replace = FALSE), ]
      
      # calculate residuals for this sample
      median.residuals <- dentition.sampled$Stress.norm - median(dentition.sampled$Stress.norm)
      
      # add them to the residuals vector
      m.residual.vec <- c(m.residual.vec, median.residuals)
      
      j <- j + 1
      
    }
    
  }
  
  # various cutoffs:
  
  # standard deviation
  m.sd <- sd(m.residual.vec)
  
  # kmeans
  km <- kmeans(sqrt(m.residual.vec^2), 2)
  m.k <- mean(km$centers)
  
  # 95% quantile
  m.ninetyfive <- quantile(sqrt(m.residual.vec^2), c(0.95))
  
  return(list(bootstrapped.residuals = m.residual.vec,
              sd = m.sd,
              kmeans = m.k,
              q95 = m.ninetyfive,
              original.teeth = teeth.list))
  
}

