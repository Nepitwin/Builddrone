*** Settings ***
Documentation     Small Robot Framework suite used by the Builddrone example.

*** Test Cases ***
Builddrone can run Robot Framework
    [Documentation]    Verify that the example suite executes successfully.
    Log    Robot Framework is running through Builddrone.
    Should Be Equal    ${1}    ${1}
