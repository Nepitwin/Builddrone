namespace Builddrone.DotnetExample.XUnitTests;

public class GreeterTests
{
    [Fact]
    public void Hello_returns_greeting()
    {
        Assert.Equal("Hello, Builddrone", Greeter.Hello("Builddrone"));
    }
}
