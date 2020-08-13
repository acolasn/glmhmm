#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Nov 25 16:06:06 2019

@author: istone

Class for fitting generalized linear models (GLMs).

Updated: April 8th, 2020

"""
#import numpy as np
import autograd.numpy as np
from scipy import optimize
from autograd import value_and_grad, hessian
import time

class GLM(object):
    
    """
    Base class for fitting generalized linear models. 
    Notation: 
        n: number of data points
        m: number of features
        c: number of classes 
        x: design matrix (nxm)
        y: observations (nxc)
        w: weights mapping x to y (mxc or mx1)

    """
    def __init__(self,n,m,c):
        self.n, self.m, self.c = n, m, c
        
    def compObs(self,x,w,normalize=True):
        """
        Computes the observation probabilities for each data point.

        Parameters
        ----------
        x : nxm array of the data (design matrix)
        w : mxc array of weights
        normalize : boolean, optional
            Determines whether or not observation probabilities are normalized. The default is True.

        Returns
        -------
        phi : nxc array of the observation probabilities

        """
        
        phi = np.exp(x@w) # get exponentials e^(wTx)
        if normalize:
            phi = np.divide(phi.T,np.sum(phi,axis=1)).T # normalize the exponentials 
        
        return phi
        
        
    def neglogli(self,x,w,y):
        """
        Calculate the total loglikelihood p(y|x)

        Parameters
        ----------
        x : nxm array of the data (design matrix)
        w : mxc array of weights
        y : nxc 1/0 array of observations

        Returns
        -------
        negative sum of the loglikelihood of the observations (y) given the data (x)

        """
        
        # assert proper shape of weight vector
        try: w.shape[1]
        except IndexError: w = w[:,np.newaxis]
            
        phi = self.compObs(x,w,normailize=False) 
        norm = np.sum(phi,axis=1) # get normalization constant 
        weightedObs = np.sum(np.multiply(phi,y),axis=1)
        log_pyx = np.log(weightedObs) - np.log(norm) # compute loglikelihood
        
        assert np.round(np.sum(np.divide(phi.T,norm)),2) == 1, 'Sum of normalized probabilities does not equal 1!'
        
        self.ll = -np.sum(log_pyx)
        
        return -np.sum(log_pyx)
    
    def fit(self,x,w,y,compHess = False):
        """
         Use gradient descent to optimize weights

        Parameters
        ----------
        x : nxm array of the data (design matrix)
        w : mxc array of weights
        y : nxc 1/0 array of observations
        compHess : boolean, optional
            sets whether or not to compute the Hessian of the weight matrix. The default is False.

        Returns
        -------
        w_new : mxc array of updated weights
        phi : nxc array of the updated observation probabilities

        """
        
        # optimize loglikelihood given weights
        w_flat = np.ndarray.flatten(w[:,1:]) # flatten weights for optimization    
        opt_log = lambda w: self.neglogli(x,w,y) # calculate log likelihood 
        OptimizeResult = optimize.minimize(value_and_grad(opt_log),w_flat, jac = "True", method = "L-BFGS-B")
       
        self.w_new = np.hstack((np.zeros((self.m,1)),np.reshape(OptimizeResult.x,(self.m,self.c-1)))) # reshape and update weights
        
        # Get updated observation probabilities 
        self.phi = self.compObs(x,w) 
        
        if compHess:
            ## compute Hessian
            hess = hessian(opt_log) # function that computes the hessian
            H = hess(self.w_new[:,1:]) # gets matrix for w_hats
            self.variance = np.sqrt(np.diag(np.linalg.inv(H.T.reshape((self.m * (self.c-1),self.m * (self.c-1)))))) # calculate variance of weights from Hessian
        
        return self.w_new,self.phi
    
    def generate_data(self,wdist=(-0.2,1.2),xdist=(-10,10),bias=True):
        
        """
        Generate simulated data (design matrix, weights, and observations) for fitting a GLM                                                      

        Parameters
        ----------
        wdist : tuple, optional
                sets high and low uniform distribution limits for randomly sampling weight values. The default is (-0.2,1.2).
        xdist : tuple, optional
                sets high and low limits for randomly sampling integer data values. The default is (-10,10).
        bias : boolean, optional
               determines whether or not to add a bias to the data. The default is True.

        Returns
        -------
        x : nxm array of the data (design matrix)
        w : mxc array of weights
        y : nxc 1/0 array of observations

        """
        
        ## generate weights
        w = np.zeros((self.m,self.c)) # initialize array
        w[:,1:] = np.random.uniform(wdist[0], high=wdist[1],size=(self.m,self.c-1)) # leave first column of weights zeros; randomly sample the rest 
        
        ## generate data
        x = np.random.randint(xdist[0], high=xdist[1],size=(self.n,self.m)) # choose length random inputs between -10 and 10
        
        ## add optional bias to weights
        if bias:
            x = np.hstack((np.ones_like(x[:,1,np.newaxis]),x)) # append bias column to left side of matrix
            w = np.vstack((np.ones_like(w[0,:])*np.hstack((np.zeros((1,1)),np.random.uniform(wdist[0], high=wdist[1],size=(1,self.c-1)))),w))
            
        ## generate observation probabilities
        phi = self.compObs(x,w) 
        
        # generate 1-D vector of observations for each n
        cumdist = phi.cumsum(axis=1) # calculate the cumulative distributions
        undist = np.random.rand(len(cumdist), 1) # generate set of uniformly distributed samples
        obs = (undist < cumdist).argmax(axis=1) # see where they "fit" in cumdist
        
        # convert to nxc matrix of binary values
        y = np.zeros((self.n,self.c))
        y[np.arange(self.n),obs] = 1
            
        return x,w,y