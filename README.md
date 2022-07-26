# mlcdc
Machine Learning for estimating Cross Domain Covariance (&amp; Correlation) relationships in coupled atmosphere-ocean DA systems


## Process

- [x] Get "true" correlations from 80 member ensemble
- [ ] Get predictors as 4 x 20 member ensemble averages of
    - precip rate, cloud fraction, total precip, total precip, total cloud
      cover, lw, sw, (fluxes?)
    - SST, MLD, wind speed, surface current speed
    - Without resampling or kernel estimation, don't have to worry about error
      in this approximation ... otherwise maybe that gets tricky?
- [ ] Make training and validation datasets:
    - flatten lon, lat, sample (1-4) to sample dimension
    - independent variables or predictors dimension (can just be labels)
    - dependent variables or output / labels on `atm_lev`, `ocn_lev`
- [ ] go with [this example](https://www.tensorflow.org/tutorials/keras/regression)

