*** Settings ***
Library           sutmaster.starter_library.StarterLibrary

*** Test Cases ***
Start Docker SUT with Config Copy
    Log To Console   Starting SUT-A with config file override...
    Start Sut        SUT-A

Start Service SUT with Config Copy
    Log To Console   Starting SUT-B with config file copy...
    Start Sut        SUT-B
