namespace Builddrone.DotnetExample;

public static class Greeter
{
    public static string Hello(string name)
    {
        if (string.IsNullOrWhiteSpace(name))
        {
            throw new ArgumentException("Name is required.", nameof(name));
        }

        return $"Hello, {name}";
    }
}
