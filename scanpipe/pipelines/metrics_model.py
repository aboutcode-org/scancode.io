#
# Copyright (C) AboutCode
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import math

# These coefficients were calculated with the notebooks and data available
# at https://github.com/aboutcode-org/healthycode/blob/main/model/npm/README.md


class npmModel:
    # We have dropped the low-impact metrics, those with a coefficient close to 0
    COEFFICIENTS = {
        "elephant_factor": -1.635941,
        "coefficient_of_variation": -1.404157,
        "total_contributors": -0.991894,
        "days_since_last_commit": 0.865738,
        "contributor_growth_rate": 0.435875,
        "commits_over_periods_rate": -0.410393,
        "total_commits": -0.330035,
        "message_size_mean": -0.320026,
        "found_file_license": 0.266483,
    }

    # Model Intercept
    Z = -0.549873845969752

    def __init__(self):
        self.coefficients = self.COEFFICIENTS.copy()
        self.z = self.Z

    def calculate_score(self, metrics: dict[str, float]) -> float:
        """
        Calculates the probability of a repository being 'Unhealthy' based on
        the pruned logistic regression model metrics.

        Parameters
        ----------
        metrics (dict): Dictionary containing the project feature names and values.

        Returns
        -------
        float: Probability score between 0.0 (Healthy) and 1.0 (Unhealthy).

        """
        z = self.z

        # Calculate the linear combination (log-odds)
        for metric, coef in self.coefficients.items():
            # FIXME. We set by default 0 if a metric is missing. Is this safe?
            value = metrics.get(metric, 0.0)
            z += coef * value

        # Apply the Sigmoid function to get the final probability
        try:
            probability = 1 / (1 + math.exp(-z))
        except OverflowError:
            # Safeguard against extreme values of z
            # FIXME Is this correct?
            probability = 0.0 if z < 0 else 1.0

        return probability
