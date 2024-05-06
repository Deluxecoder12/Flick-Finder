#include<iostream>
#include<vector>

using namespace std;

int main(){
    vector<int> numbers = {1, 2, 3, 4, 5};

    for(int i : numbers){
        cout << i << endl;
    }

    return 0;
}