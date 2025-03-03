class Solution:
    def minCost(self, n: int, cost: List[List[int]]) -> int:
        n = len(cost)

        def f(cost, house, prev_color, ds, flag):
            if house < 0:
                return 0
            
            mini = float('inf')
            
            for color in range(3):  
                if color != prev_color:  
                    mirror_idx = len(cost) - 1 - house  
                    
                    
                    if house < flag and ds[mirror_idx] == color:
                        continue  

                    ds[house] = color  
                    rec_cost = cost[house][color] + f(cost, house - 1, color, ds, flag)
                    mini = min(mini, rec_cost)  
                    ds[house] = None
            
            return mini
        
        def tab(cost):
            dp = [[0 for _ in range(3)] for _ in range(len(cost))]
            
        n = len(cost)
        return f(cost,n-1, 3, {}, n//2 )

    def tab(cost):
        