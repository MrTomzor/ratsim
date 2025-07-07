from roslike_unity_connector.bag import MessageBag

import sys

if __name__ == "__main__":
    save_filename = sys.argv[1]
    
    bag = MessageBag(save_filename)
    print("num steps: " + str(len(bag.steps)))


    for step in bag.steps:
        print(step)

