arr=[10,8,16,26]

reverse=[]

def reverse_element(arr):
    for i in range(len(arr)-1,-1, -1):
        reverse.append(arr[i])


reverse_element(arr)
print(reverse)