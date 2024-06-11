from ogzaf import macro_params, income
from ogzaf import input_output as io
import os
import numpy as np
from ogcore import txfunc, demographics
from ogcore.utils import safe_read_pickle, mkdirs
import pkg_resources

CUR_DIR = os.path.dirname(os.path.realpath(__file__))


class Calibration:
    """OG-ZAF calibration class"""

    def __init__(
        self,
        p,
        estimate_tax_functions=False,
        estimate_beta=False,
        estimate_chi_n=False,
        estimate_pop=False,
        tax_func_path=None,
        iit_reform={},
        guid="",
        data="cps",
        client=None,
        num_workers=1,
        demographic_data_path=None,
        output_path=None,
    ):
        """
        Constructor for the Calibration class.

        Args:
            p (OG-Core Specifications object): model parameters
            estimate_tax_functions (bool): whether to estimate tax
                function parameters
            estimate_beta (bool): whether to estimate beta
            estimate_chi_n (bool): whether to estimate chi_n
            estimate_pop (bool): whether to estimate population
            tax_func_path (str): path to tax function parameter
                estimates
            iit_reform (dict): IIT reform dictionary
            guid (str): unique identifier for reform
            data (str): type of data to use in tax function
            client (Dask client object): client
            num_workers (int): number of workers
            demographic_data_path (str): path to save demographic data
            output_path (str): path to save output to

        Returns:
            None

        """
        # Create output_path if it doesn't exist
        if output_path is not None:
            if not os.path.exists(output_path):
                os.makedirs(output_path)
        self.estimate_tax_functions = estimate_tax_functions
        self.estimate_beta = estimate_beta
        self.estimate_chi_n = estimate_chi_n
        self.estimate_pop = estimate_pop
        if estimate_tax_functions:
            self.tax_function_params = self.get_tax_function_parameters(
                p,
                iit_reform,
                guid,
                data,
                client,
                num_workers,
                run_micro=True,
                tax_func_path=tax_func_path,
            )
        # if estimate_beta:
        #     self.beta_j = estimate_beta_j.beta_estimate(self)
        # if estimate_chi_n:
        #     chi_n = self.get_chi_n()

        # Macro estimation
        self.macro_params = macro_params.get_macro_params()

        # io matrix and alpha_c
        if p.I > 1:  # no need if just one consumption good
            alpha_c_dict = io.get_alpha_c()
            # check that model dimensions are consistent with alpha_c
            assert p.I == len(list(alpha_c_dict.keys()))
            self.alpha_c = np.array(list(alpha_c_dict.values()))
        else:
            self.alpha_c = np.array([1.0])
        if p.M > 1:  # no need if just one production good
            io_df = io.get_io_matrix()
            # check that model dimensions are consistent with io_matrix
            assert p.M == len(list(io_df.keys()))
            self.io_matrix = io_df.values
        else:
            self.io_matrix = np.array([[1.0]])

        # eta estimation
        # self.eta = transfer_distribution.get_transfer_matrix()

        # zeta estimation
        # self.zeta = bequest_transmission.get_bequest_matrix()

        # demographics
        if estimate_pop:
            self.demographic_params = demographics.get_pop_objs(
                p.E,
                p.S,
                p.T,
                0,
                99,
                initial_data_year=p.start_year - 1,
                final_data_year=p.start_year,
                GraphDiag=False,
                download_path=demographic_data_path,
            )

            # demographics for 80 period lives (needed for getting e below)
            demog80 = demographics.get_pop_objs(
                20,
                80,
                p.T,
                0,
                99,
                initial_data_year=p.start_year - 1,
                final_data_year=p.start_year,
                GraphDiag=False,
            )

        # earnings profiles
        self.e = income.get_e_interp(
            p.S,
            self.demographic_params["omega_SS"],
            demog80["omega_SS"],
            p.lambdas,
            plot_path=output_path,
        )

    # method to return all newly calibrated parameters in a dictionary
    def get_dict(self):
        dict = {}
        # if self.estimate_beta:
        #     dict["beta_annual"] = self.beta
        # if self.estimate_chi_n:
        #     dict["chi_n"] = self.chi_n
        # dict["eta"] = self.eta
        # dict["zeta"] = self.zeta
        # dict.update(self.macro_params)
        dict["e"] = self.e
        dict["alpha_c"] = self.alpha_c
        dict["io_matrix"] = self.io_matrix
        if self.estimate_pop:
            dict.update(self.demographic_params)

        return dict
